import os
import re
import hcl2
from tqdm import tqdm
from services.thousandeyes_service import get_account_groups


def normalize_name(name):
    # Replace non-alphanumeric characters with underscores
    normalized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Replace multiple consecutive underscores with a single underscore
    normalized = re.sub(r'_+', '_', normalized)
    # Optionally, strip leading/trailing underscores
    return normalized.strip('_')


def to_snake_case(name):
    # Converts CamelCase or mixedCase to snake_case
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def parse_terraform_file(file_path):
    with open(file_path, 'r') as tf_file:
        content = tf_file.read()
    parsed = hcl2.loads(content)
    return parsed

def generate_provider_block(alias_name, account_group_id):
    return {
        'provider': {
            'thousandeyes': {
                'alias': alias_name,
                'token': '${var.thousandeyes_token}',
                'account_group_id': account_group_id
            }
        }
    }

def generate_resource_block(test, alias_name, existing_resource_config=None):
    
    resource_type = f"thousandeyes_{test.type.replace('-', '_')}"
    resource_name = normalize_name(test.testName)
    payload = test.dict(exclude_none=True, exclude={'agentsLabel', 'agents', 'type', 'accountGroupName', 'update', 'delete'})

    # Build the resource configuration
    resource_config = {}
    for key, value in payload.items():
        tf_key = to_snake_case(key)
        resource_config[tf_key] = value

    # Add agents if appropriate
    if test.type != 'bgp':
        if test.agentsLabel.strip():  # AgentsLabel is not empty
            if test.agents:
                resource_config['agents'] = [{'agent_id': agent['agentId']} for agent in test.agents if 'agentId' in agent]
        else:  # AgentsLabel is empty; keep existing agents if any
            if existing_resource_config and 'agents' in existing_resource_config:
                resource_config['agents'] = existing_resource_config['agents']
            else:
                # No existing agents; we may decide to leave agents empty or handle accordingly
                pass

    # Add provider alias
    if alias_name:
        resource_config['provider'] = f'thousandeyes.{alias_name}'
    else:
        provider = existing_resource_config['provider']
        resource_config['provider'] = provider.strip("${}")
        pass

    return {resource_type: {resource_name: resource_config}}

def update_terraform(file_path, test_objects, accounts):

    # ya llegamso aqui, lo que tenemos que hacer es ver si se hara update o delete y quitarle esas banderas

    acc_aids = get_account_groups()
    labels_agents_mapping = get_agents_from_label(accounts_names=accounts, acc_aids=acc_aids)


    # Parse existing Terraform configuration
    if os.path.exists(file_path):
        terraform_data = parse_terraform_file(file_path)
    else:
        terraform_data = {}

    existing_providers = {}
    existing_resources = {}

    # Extract existing providers
    if 'provider' in terraform_data:
        for provider in terraform_data['provider']:
            for key, value in provider.items():
                alias = value.get('alias')
                if alias:
                    existing_providers[alias] = value

    # Extract existing resources
    if 'resource' in terraform_data:
        for resource in terraform_data['resource']:
            for resource_type, resources in resource.items():
                for resource_name, resource_config in resources.items():
                    key = f"{resource_type}.{resource_name}"
                    existing_resources[key] = resource_config

    # Update providers -- esta condicion en teoria es imposible que exista porque en vez de hacer update, haria el create
    # entonces el mismo test se crearia pero en un AG diferente
    for account_name in accounts:
        account_group_id = acc_aids.get(account_name)
        alias_name = re.sub(r'[^a-zA-Z0-9]', '', account_name)

        if alias_name not in existing_providers:
            provider_block = generate_provider_block(alias_name, account_group_id)
            terraform_data.setdefault('provider', []).append(provider_block)
            existing_providers[alias_name] = provider_block['provider']['thousandeyes']

    # Update resources
    for test in tqdm(test_objects, desc="Updating Terraform", unit="test"):

        if test.delete:

            resource_type = f"thousandeyes_{test.type.replace('-', '_')}"
            resource_name = normalize_name(test.testName)
            key = f"{resource_type}.{resource_name}"

            del existing_resources[key]

        elif test.update:

            if test.type != 'bgp':
                if test.agentsLabel.strip():
                    # Process agentsLabel
                    label_name, account_group = test.agentsLabel.split("-->")
                    label_name, account_group = label_name.strip(), account_group.strip()
                    aid = acc_aids[account_group]
                    test.agents = labels_agents_mapping.get((label_name, str(aid)), {}).get('agents', [])
                else:
                    # AgentsLabel is empty, do not modify test.agents; leave it empty
                    account_group = " "
            else:
                account_group = test.accountGroupName
                aid = acc_aids[account_group]

            # Aqui si el test en el update no le ponen label entonces el alias name no va a existir pero en teoria no importa porque
            # si se encuentra un test entonces ya deberia de tener ese resource, no se puede modificar 
            alias_name = re.sub(r'[^a-zA-Z0-9]', '', account_group)

            # Get the existing resource configuration if it exists
            resource_type = f"thousandeyes_{test.type.replace('-', '_')}"

            resource_name = normalize_name(test.testName)
            key = f"{resource_type}.{resource_name}"
            existing_resource_config = existing_resources.get(key, None)

            resource_block = generate_resource_block(test, alias_name, existing_resource_config=existing_resource_config)
            
            
            # Update existing resource or add new
            existing_resources[key] = resource_block[resource_type][resource_name]

        
    # Reconstruct the Terraform data
    terraform_data['resource'] = []
    for key, resource_config in existing_resources.items():
        resource_type, resource_name = key.split('.')
        terraform_data['resource'].append({
            resource_type: {
                resource_name: resource_config
            }
        })

    # Write back to main.tf
    with open(file_path, 'w') as tf_file:
        tf_content = ''
        # Write providers
        if 'provider' in terraform_data:
            for provider in terraform_data['provider']:
                for provider_name, provider_config in provider.items():
                    tf_content += f'provider "{provider_name}" {{\n'
                    for k, v in provider_config.items():
                        tf_content += f'  {k} = "{v}"\n'
                    tf_content += '}\n\n'

        # Write resources
        if 'resource' in terraform_data:
            for resource in terraform_data['resource']:
                for resource_type, resources in resource.items():
                    for resource_name, resource_config in resources.items():
                        tf_content += f'resource "{resource_type}" "{resource_name}" {{\n'
                        for k, v in resource_config.items():
                            if isinstance(v, bool):
                                tf_content += f'  {k} = {"true" if v else "false"}\n'
                            elif isinstance(v, str):
                                if k == 'provider':
                                    if '${' in v:
                                        v = v.strip("${}")
                                    tf_content += f'  {k} = {v}\n'
                                else:
                                    tf_content += f'  {k} = "{v}"\n'
                            elif isinstance(v, list) and k == 'agents':
                                for agent in v:
                                    tf_content += '  agents {\n'
                                    for ak, av in agent.items():
                                        tf_content += f'    {ak} = {av}\n'
                                    tf_content += '  }\n'
                            else:
                                tf_content += f'  {k} = {v}\n'
                        tf_content += '}\n\n'
        tf_file.write(tf_content)

    print(f'Terraform configuration updated: {file_path}')
