from services.logging_service import my_logger
from tqdm import tqdm
from config.configuration import config
import os



def create_import_terraform(existing_tests:dict) -> bool:

    
    # Set the path to the existing terraform project
    file_path = os.path.join(os.getcwd(), config.terraform_project_path)

    import_file = os.path.join(file_path, "imports.tf")
    providers_file = os.path.join(file_path, "providers.tf")
    vars_file = os.path.join(file_path, "variables.tf")
    
    # Parse existing providers to avoid duplicates
    with open(vars_file, 'a') as vars_file:
        
        token_var_str = 'variable "token" {\n'
        token_var_str += f'    description = "ThousandEyes API Token"\n'
        token_var_str += f'    type        = string\n'
        token_var_str += f'    default = "{config.API_TOKEN}"\n'
        token_var_str += '}\n\n'


        vars_file.write(token_var_str)


    # Parse existing providers to avoid duplicates
    with open(providers_file, 'a') as prov_file:

        
        terraform_str = 'terraform {\n  required_providers {\n    thousandeyes = {\n'
        terraform_str += f'      source  = "thousandeyes/thousandeyes"\n      version = "{config.te_tf_version}"'
        terraform_str += '    }\n  }\n} \n\n'

        prov_file.write(terraform_str)

        for account in existing_tests.keys():

            prov_file.write('provider "thousandeyes" {\n')
            prov_file.write(f'  alias = "{account[0]}"\n')
            prov_file.write(f'  token = var.token\n')
            prov_file.write(f'  account_group_id = "{account[1]}"\n')
            prov_file.write('}\n\n')

    # Open the import file in append mode
    with open(import_file, 'a') as tf_file:

        for account_group, tests in tqdm(existing_tests.items(), desc="Generating Terraform File", unit=" account groups"):

            ag_name = account_group[0]

            for test in tests:

                test_name = test[0]
                test_id = test[1]
                resource_type = test[2]

                terraform_str = 'import { \n'
                terraform_str += f'  provider = thousandeyes.{ag_name}\n'
                terraform_str += f'  to = {resource_type}.{test_name}\n' # to = thousandeyes_http_server.AHCTesting
                terraform_str += f'  id = {test_id}\n'

                terraform_str += "}\n\n"
                tf_file.write(terraform_str)

    print(f'Terraform configuration updated: {file_path}')
    my_logger.info(f'Terraform configuration updated at {file_path}')

    return True
