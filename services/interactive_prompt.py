import time
from colorama import Fore, Style, Back

from config.configuration import config
from services.thousandeyes_service import get_account_groups, get_existant_tests
from services.logging_service import my_logger
from controller.create_terraform import create_import_terraform

def banner():
    with open('Assets/banner.txt', 'r') as file:
        banner = file.read()
    print(banner)

def select_accounts() -> dict:

    print(f'\n{Back.YELLOW}[INFO]{Style.RESET_ALL} Fetching account groups from ThousandEyes...')
    
    confirmed = False

    #Get account groups for the specified org at the config file
    accounts = get_account_groups()

    if accounts:

        account_list = list(accounts.keys())

        while not confirmed:

            print(f"\nThese are the account groups within {Fore.MAGENTA}{config.org_name}{Style.RESET_ALL}:")
            
            for i, acc in enumerate(accounts, 1):
                print(f'  {i}. {acc}')

            selected_accounts = input(f"\n{Fore.YELLOW}Enter{Style.RESET_ALL} the numbers of the account groups you want to select (e.g., 1-3,5): ")


            # Parse the input to handle ranges (e.g., 1-3,5 -> 1, 2, 3, 5)
            def parse_selection(input_str):
                selection = set()
                ranges = input_str.split(',')
                for r in ranges:
                    if '-' in r:
                        start, end = map(int, r.split('-'))
                        selection.update(range(start, end + 1))
                    else:
                        selection.add(int(r))
                return selection

            selected_numbers = parse_selection(selected_accounts)

            # Filter the accounts based on the user's input
            accounts = {account_list[i - 1]: accounts[account_list[i - 1]] for i in selected_numbers if i <= len(account_list)}

            # Display the selected account groups
            print(f"\n{Fore.CYAN}You selected{Style.RESET_ALL} the following account groups:")
            for acc in accounts.keys():
                print(f'  + {acc}')
            
            confirmation = input("\nAre this the right account groups? (y/n)")

            if confirmation.lower() in ['y','yes']:
                confirmed = True

            
        return accounts
    
    return accounts



#############################
#           MAIN
#############################

def user_prompt():

    try:
        
        # Variables
        mission = 1

        # Functions
        banner()
        

        # User interaction
        while mission < 2 and mission > 0:

            print('\n'+'-'*100)

            #La acción a ejecutar
            print("\nWhat would you like to do?\n  1. Get TE tests\n  2. Quit")
            mission = int(input(f"\n{Fore.YELLOW}Enter{Style.RESET_ALL} the corresponding number: "))

            my_logger.info(f'User selected mission {mission}')

            #Get template
            if mission == 1:
                
                # The user selects the AG from which gather all data
                account_groups = select_accounts()
                my_logger.info(f'User selected the following account groups {account_groups.keys()}')


                # Ahora el flow sera el siguiente:
                # 1. Obtener los tests de esos AG,
                tests = get_existant_tests(account_groups)
                my_logger.info(f'Number of tests obtained: {len(tests)}')
                
                # 2. Generar el terraform file con esos tests

                # Core functionality
                start = time.time()
                print(f'\n{Back.GREEN}[INFO]{Style.RESET_ALL} Generating Terraform import blocks...')
                my_logger.info('Generating Terraform import blocks')

                tests_created = create_import_terraform(existing_tests=tests)

                if tests_created:

                    print(f'\n{Back.GREEN}[INFO]{Style.RESET_ALL} All tests have been added to the Terraform file.')
                    my_logger.info('All tests have been added to the Terraform file.')


                roundtrip = time.time() - start

                print(f'\n{Back.GREEN}[INFO]{Style.RESET_ALL} File created in {roundtrip/60} minutes')
                my_logger.info(f'File created in {roundtrip/60} minutes')


            #Exit
            else:
                print('Exiting the app, thanks for using it.')

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
