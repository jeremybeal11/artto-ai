from helpers.utils import *
from helpers.llm_helpers import *
from helpers.nft_data_helpers import *
from helpers.farcaster_helpers import *
from helpers.coinbase_helpers import *
from helpers.twitter_helpers import *
from helpers.artto_decision_helpers import *

import logging

logger = logging.getLogger(__name__)

async def process_webhook(webhook_data):
    try:
        # Skip if not an ADDRESS_ACTIVITY event
        if webhook_data.get('type') != 'ADDRESS_ACTIVITY':
            logger.info(f"Skipping - event type is not ADDRESS_ACTIVITY")
            return {
                'status': 'skipped',
                'reason': 'Not ADDRESS_ACTIVITY event'
            }
        
        activity = webhook_data['event']['activity'][0]

        # Skip if not an ERC721 token transfer
        if not ('erc721TokenId' in activity or 'erc1155Metadata' in activity):
            logger.info(f"Skipping - not an ERC721 or ERC1155 token transfer")
            return {
                'status': 'skipped',
                'reason': 'Not ERC721 or ERC1155 transfer'
            }
        
        if 'erc721TokenId' in activity:
            token_id = str(int(activity['erc721TokenId'], 16))  # Convert hex to decimal
            event_type = "ERC721_TRANSFER"
        elif 'erc1155Metadata' in activity:
            token_id = str(int(activity['erc1155Metadata'][0]['tokenId'], 16))
            event_type = "ERC1155_TRANSFER"
        else:
            print("No token ID found")
            return {
                'status': 'skipped',
                'reason': 'No token ID found'
            }
        
        to_address = activity['toAddress']

        # Only process if this is an incoming transfer to our wallet
        if to_address.lower() not in [os.getenv('ARTTO_ADDRESS_SEPOLIA').lower(), os.getenv('ARTTO_ADDRESS_MAINNET').lower()]:
            logger.info(f"Skipping - transfer not to our wallet address")
            return {
                'status': 'skipped', 
                'reason': 'Not incoming transfer'
            }

        webhook_network = webhook_data['event']['network']

        # Map webhook network names to simplehash network names
        network_mapping = {
            'BASE_MAINNET': 'base',
            'ETH_MAINNET': 'ethereum', 
            'SHAPE_MAINNET': 'shape',
            'ZORA_MAINNET': 'zora'
        }

        # Get simplehash network name from mapping, default to webhook network name
        simplehash_network = network_mapping.get(webhook_network, webhook_network)
        
        # All mainnet networks use the same wallet address
        current_wallet_address = os.getenv('ARTTO_ADDRESS_MAINNET')
        
        if not webhook_network in network_mapping:
            return {
                'status': 'skipped',
                'reason': f'Unsupported network: {webhook_network}'
            }
        logger.info(f"Processing {webhook_network}")

        from_address = activity['fromAddress']
        contract_address = activity['rawContract']['address']
        
        post_content = f"I just received token #{token_id} from {from_address}!"
        
        print(post_content)
        print("network:", webhook_network)
        print("contract_address:", contract_address)
        print("token_id:", token_id)

        try:
            set_wallet_activity(
                event_type=event_type, 
                from_address=from_address, 
                to_address=current_wallet_address, 
                token_id=token_id, 
                network=webhook_network, 
                contract_address=contract_address, 
                amount=1
            )
        except Exception as e:
            print(f"Error setting wallet activity: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

        sender_address = from_address

        response = await get_artwork_analysis_and_metadata(
            simplehash_network,
            contract_address,
            token_id
        )

        artwork_analysis = response["artwork_analysis"]
        metadata = response["metadata"]

        nft_details = {
            "artwork_analysis": artwork_analysis,
            "image_small_url": metadata["image_small_url"],
            "chain": simplehash_network,
            "contract_address": contract_address,
            "token_id": token_id,
            "metadata": metadata
        }

        score_details = await get_total_score(artwork_analysis, nft_details, sender_address)

        print("Getting final decision")
        final_decision = await get_final_decision(artwork_analysis, metadata, from_address, score_details)

        decision = final_decision.decision
        rationale_post = final_decision.rationale_post

        try:
            reward_points = score_details["reward_points"]
        except:
            reward_points = 0
        print("Reward points:", reward_points)
        store_nft_scores(nft_details, score_details, final_decision)

        print("Decision:", decision)
        print("Rationale:", rationale_post)
        

        return {
            'status': 'success',
            'decision': decision,
            'rationale': rationale_post,
            'metadata': metadata,
            'artwork_analysis': artwork_analysis
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")

        return {
            'status': 'error',
            'error': str(e)
        }

async def process_neynar_webhook(webhook_data):
    data = webhook_data      
    # Extract relevant data from webhook payload
    cast = data.get('data', {})

    print("Raw cast data:", cast)

    cast_details = get_cast_details(cast)
    print("Responding to cast:", cast_details)
    post_params = generate_post_params()
    posts_replied_to = get_all_posts_replied_to()
    if any(p['parent_id'] == cast["hash"] for p in posts_replied_to):
        print("Already replied to this parent")
        return
    reply, nft_details, score_details = await get_reply(cast_details, post_params)
    react_cast('like', cast["hash"])
    print("Reply:", reply)
    response = post_long_cast(reply, parent=cast["hash"])
    if score_details and nft_details:
        store_nft_scores(nft_details, score_details)