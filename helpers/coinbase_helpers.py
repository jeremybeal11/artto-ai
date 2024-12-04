import os

from cdp import *

# # Zora WOW Token Actions
# from cdp_agentkit_core.actions.wow.create_token import *
# from cdp_agentkit_core.actions.wow.buy_token import *
# from cdp_agentkit_core.actions.wow.sell_token import *

# # Core actions
# from cdp_agentkit_core.actions.deploy_token import *
# from cdp_agentkit_core.actions.register_basename import *
# from cdp_agentkit_core.actions.trade import *
# from cdp_agentkit_core.actions.transfer import *


from dotenv import load_dotenv

load_dotenv('.env.local')

Cdp.configure(os.getenv('COINBASE_API_KEY_NAME'), os.getenv('COINBASE_API_KEY_PRIVATE_KEY'))

wallet_id_sepolia = os.getenv('WALLET_ID_SEPOLIA')
wallet_id_mainnet = os.getenv('WALLET_ID_MAINNET')

wallet_sepolia = Wallet.fetch(wallet_id_sepolia)
wallet_mainnet = Wallet.fetch(wallet_id_mainnet)

file_path_sepolia = "artto_sepolia_seed.json"
file_path_mainnet = "artto_mainnet_seed.json"
wallet_sepolia.load_seed(file_path=file_path_sepolia)
wallet_mainnet.load_seed(file_path=file_path_mainnet)

def fetch_wallet(wallet_id, file_path):
    fetched_wallet = Wallet.fetch(wallet_id)
    fetched_wallet.load_seed(file_path=file_path)

    return fetched_wallet

def artto_setup():
    # Create a new wallet 
    # https://artto-ai-85.localcan.dev
    artto_wallet = Wallet.create(network_id="base-mainnet")
    print(f"Wallet successfully created: {artto_wallet}")

    address = artto_wallet.default_address
    print(f"Address: {address}")

    file_path = "artto_mainnet_seed.json"
    artto_wallet.save_seed(file_path, encrypt=True)
    print(f"Seed for wallet {artto_wallet.id} successfully saved to {file_path}.")

    artto_webhook = artto_wallet.create_webhook(os.getenv('ARTTO_COINBASE_WEBHOOK_URL'))

    #TODO(ADD EVENT TYPE: erc721_transfer)

    print(f"Webhook successfully created: {artto_webhook}")

def get_abi(network_id, contract_address):
    import requests
    import json

    base_url = f"https://{'api-sepolia' if network_id == 'base-sepolia' else 'api'}.basescan.org/api"
    params = {
        "module": "contract",
        "action": "getabi", 
        "address": contract_address,
        "apikey": os.getenv('BASESCAN_API_KEY')
    }

    response = requests.get(base_url, params=params)
    response_json = response.json()

    if response_json["status"] == "1" and response_json["message"] == "OK":
        abi = json.loads(response_json["result"])
    else:
        abi = None
    return abi

def get_implementation_address(network_id, contract_address):
    abi = get_abi(network_id, contract_address)
    invoke_contract = wallet.invoke_contract(
        contract_address=contract_address,
        method="implementation",
        abi=abi,
    )
    invoke_contract.wait()
    print(invoke_contract)

def transfer_nft(wallet, network_id, contract_address, from_address, to_address, token_id):
    try:
        print("Trying to transfer NFT")
        abi = get_abi(network_id, contract_address)
        invoke_contract = wallet.invoke_contract(
            contract_address=contract_address,
            method="transferFrom", 
            abi=abi,
            args={"from":from_address, "to":to_address, "tokenId":token_id}
        )
        invoke_contract.wait()
        return f"Successfully transferred NFT {token_id} from {from_address} to {to_address}"
    except Exception as first_error:
        print(f"Error transferring NFT: {str(first_error)}")
        print("Trying again with implementation contract")
        try:
            # If first attempt fails, try getting implementation contract
            implementation_contract = SmartContract.read(
                network_id=network_id,
                contract_address=contract_address,
                method="implementation",
                abi=abi
            )
            
            # Get ABI of implementation contract
            implementation_abi = get_abi(network_id, implementation_contract)
            
            # Try transfer with implementation contract ABI but proxy address
            invoke_contract = wallet.invoke_contract(
                contract_address=contract_address,
                method="transferFrom",
                abi=implementation_abi, 
                args={"from":from_address, "to":to_address, "tokenId":token_id}
            )
            invoke_contract.wait()
            return f"Successfully transferred NFT {token_id} from {from_address} to {to_address}"
        except Exception as e:
            error_msg = f"Error transferring NFT: {str(e)}"
            if hasattr(e, 'api_message'):
                error_msg += f" - {e.api_message}" 
            return error_msg


if __name__ == "__main__":
    # artto_setup()
    wallet = fetch_wallet(os.getenv('WALLET_ID_MAINNET'), "artto_mainnet_seed.json")

    # response = transfer_nft(wallet=wallet,
    #              network_id="base-mainnet", 
    #              contract_address="0x3d8683Bbf9CaE7ad0441b65ddCadEC3850d1256E", 
    #              from_address=wallet.default_address.address_id, 
    #              to_address="0x9424116b9D61d04B678C5E5EddF8499f88ED9ADE", 
    #              token_id="8359")
    
    # print(response)


