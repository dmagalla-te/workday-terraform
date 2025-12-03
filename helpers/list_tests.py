import csv
import sys
from pathlib import Path

if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.connector_service import get_data
from config.configuration import config
from services.logging_service import my_logger
from services.thousandeyes_service import get_account_groups, URL

def get_all_tests() -> list:
    
    """Fetch all ThousandEyes tests and write that info at a csv file"""

    tests_list = []

    # We need to fetch all the account groups first
    account_groups = get_account_groups()

    for name, aid in account_groups.items():

        params = {"aid": aid}

        try:
            status_code, tests = get_data(headers=config.headers, endp_url=f'{URL}tests', params=params)

            if status_code != 200:
                my_logger.error(f"Failed to fetch tests for account group {name} (AID: {aid}). Status code: {status_code}")
                continue
        
            if isinstance(tests, dict) and "tests" in tests:
                for test in tests.get("tests", []):
                    if isinstance(test, dict):
                        single_test = [name, aid, test.get("testName"), test.get("testId"), test.get("type")]
                        tests_list.append(single_test)


        except Exception as e:
            my_logger.error(f"Error fetching tests: {e}")
            raise e
        
    return tests_list
        

def write_to_csv(formatted_tests:list):
    """Write the fetched tests to a CSV file"""

    with open('tests_list.csv', 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        
        spamwriter.writerow(['Account Name', 'Account ID', 'Test Name', 'Test ID', 'Test Type'])
        for test in formatted_tests:
            spamwriter.writerow(test)

if __name__ == "__main__":
    
    formatted_tests = get_all_tests()
    write_to_csv(formatted_tests)