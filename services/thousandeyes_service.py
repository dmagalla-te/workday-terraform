import re

from services.connector_service import get_data
from config.configuration import config
from services.logging_service import my_logger

URL = "https://api.thousandeyes.com/v7/"

TF_MAP = {
    "agent-to-server": "thousandeyes_agent_to_server",
    "agent-to-agent": "thousandeyes_agent_to_agent",
    "bgp": "thousandeyes_bgp",
    "dns-server": "thousandeyes_dns_server",
    "dns-trace": "thousandeyes_dns_trace",
    "dnssec": "thousandeyes_dnssec",
    "http-server": "thousandeyes_http_server",
    "page-load": "thousandeyes_page_load",
    "web-transactions": "thousandeyes_web_transaction",
    "api": "thousandeyes_api",
    "ftp-server": "thousandeyes_ftp_server",
    "sip-server": "thousandeyes_sip_server",
    "voice": "thousandeyes_voice"
}


def format_terraform_identifier(
    raw_value: str | None,
    fallback_prefix: str = "te",
    *,
    names_seen: set[str] | None = None,
    unique_hint: str | None = None,
) -> str:
    """Normalize names so they are Terraform-friendly and optionally unique."""

    if not raw_value:
        base = fallback_prefix
    else:
        base = raw_value.strip().lower()
        base = re.sub(r"[^\w\s-]", "", base)
        base = re.sub(r"[\s-]+", "_", base)
        base = base.strip("_") or fallback_prefix

    if base[0].isdigit():
        base = f"{fallback_prefix}_{base}"

    candidate = base
    if names_seen is None:
        return candidate

    def sanitize_hint(value: str) -> str:
        hint = value.strip().lower()
        hint = re.sub(r"[^\w\s-]", "", hint)
        hint = re.sub(r"[\s-]+", "_", hint)
        return hint.strip("_")

    if candidate in names_seen:
        if unique_hint:
            hint = sanitize_hint(unique_hint)
            if hint:
                candidate_with_hint = f"{candidate}_{hint}"
                if candidate_with_hint[0].isdigit():
                    candidate_with_hint = f"{fallback_prefix}_{candidate_with_hint}"
                if candidate_with_hint not in names_seen:
                    candidate = candidate_with_hint

    suffix = 2
    while candidate in names_seen:
        candidate = f"{base}_{suffix}"
        if candidate[0].isdigit():
            candidate = f"{fallback_prefix}_{candidate}"
        suffix += 1

    return candidate


def get_account_groups() -> dict:

    accounts = {}

    try:

        status, account_groups = get_data(headers=config.headers, endp_url=URL + "account-groups", params={})

        if account_groups and status == 200:

            if "accountGroups" in account_groups and isinstance(account_groups["accountGroups"], list):

                for acc in account_groups["accountGroups"]:

                    if isinstance(acc,dict) and acc.get("organizationName") == config.org_name:

                        accounts.update({acc.get("accountGroupName"): acc.get("aid")})

            return accounts
        
        else:
            
            my_logger.error(f"Failed to fetch account groups. Status code: {status}, Response: {account_groups}")
            return accounts
        
    except Exception as e:
        
        my_logger.error(f"Error fetching account groups: {e}")
        return accounts


def get_existant_tests(account_groups: dict):

    """
    Necesito: alias, aid , testname, type y test id para hacer el import, entonces lo que pudiera hacer seria: 

    tests = {
        ("sw_team", "1091056"): [["AHCTesting", "7486301","http_Server"], ["GettingStarted", "3015887","agent_to_Agent"]],
        ("danis_sandbox", "2098765"): [["mx_test", "8564321","http_Server"]]
    }

    Igual y el type ya lo pudiera meter mappeado pero es lo mismo, ej: thousandeyes_http_server
    """

    try:
        existing_tests = {}
        account_aliases: set[str] = set()
        formatted_test_names: set[str] = set()

        for acc_name, aid in account_groups.items():
            
            alias = format_terraform_identifier(
                acc_name,
                fallback_prefix="account",
                names_seen=account_aliases,
                unique_hint=str(aid),
            )
            
            account_aliases.add(alias)
            
            url = f'{URL}tests'
            status, tests = get_data(config.headers, endp_url=url, params={"aid": aid})

            if status == 200 and isinstance(tests, dict):

                for test in tests.get("tests", [{}]):
                    
                    if isinstance(test, dict):

                        if test.get("liveShare", False) or test.get("savedEvent", False):
                            # Not a valid test
                            continue
                        
                        # Valid test will be added to the list
                        test_type = test.get("type")
                        test_id = test.get("testId")
                        test_name = test.get("testName")

                        if not test_type or not test_id or not test_name:
                            my_logger.warning("Skipping test with incomplete metadata: %s", test)
                            continue

                        resource_name = format_terraform_identifier(
                            test_name,
                            fallback_prefix="test",
                            names_seen=formatted_test_names,
                            unique_hint=str(test_id),
                        )
                        formatted_test_names.add(resource_name)
                        resource_type = TF_MAP.get(test_type, "thousandeyes_unknown")

                        existing_tests.setdefault((alias, aid), []).append([resource_name, str(test_id), resource_type])

            else:
                msg = f"Failed to retrieve tests from {acc_name} - status: {status} - {tests}"
                my_logger.warning(msg)

    except Exception as e:
        raise e

    my_logger.info(f'Total tests fetched: {sum(len(tests) for tests in existing_tests.values())}')
    
    return existing_tests



