import csv
import sys
from pathlib import Path

if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.connector_service import get_data
from config.configuration import config
from services.logging_service import my_logger
from services.thousandeyes_service import get_account_groups, URL

def get_all_agents() -> list:
    
    """Fetch all ThousandEyes agents and write that info at a csv file"""

    agents_list = []

    # We need to fetch all the account groups first
    account_groups = get_account_groups()

    for name, aid in account_groups.items():

        params = {"aid": aid, "agentTypes":"enterprise,enterprise-cluster"}

        try:

            status_code, agents = get_data(headers=config.headers, endp_url=f'{URL}agents', params=params)

            if status_code != 200:
                my_logger.error(f"Failed to fetch agents for account group {name} (AID: {aid}). Status code: {status_code}")
                continue
        
        
            if isinstance(agents, dict) and "agents" in agents:
                for agent in agents.get("agents", []):
                    if isinstance(agent, dict):
                        single_agent = [name, aid, agent.get("agentName"), agent.get("agentId"), agent.get("agentType"), agent.get("location")]
                        agents_list.append(single_agent)

        except Exception as e:
            my_logger.error(f"Error fetching agents: {e}")
            raise e
        
    return agents_list
        

def write_to_csv(formatted_agents:list):
    """Write the fetched agents to a CSV file"""

    with open('agents_list.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        
        writer.writerow(['Account Name', 'Account ID', 'Agent Name', 'Agent ID', 'Agent Type', 'Agent Location'])

        for agent in formatted_agents:
            writer.writerow(agent)

if __name__ == "__main__":
    
    formatted_agents = get_all_agents()
    write_to_csv(formatted_agents)