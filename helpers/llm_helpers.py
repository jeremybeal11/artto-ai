from openai import OpenAI
import os
import asyncio
import json
import math

from helpers.nft_data_helpers import *
from helpers.prompts.llm_prompts import *
from helpers.artto_decision_helpers import *
from helpers.scoring_criteria_schema import *
from helpers.spam_tweet_schema import *
from helpers.wallet_analysis import *

client = OpenAI(
    api_key=os.getenv('OPENROUTER_API_KEY'),
    base_url=os.getenv('OPENROUTER_BASE_URL')
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_nft_opinion",
            "description": "Get the opinion of an NFT provided by as a link by the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "network": {"type": "string"},
                    "contract_address": {"type": "string"},
                    "token_id": {"type": "string"},
                },
                "required": ["network", "contract_address", "token_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function", 
        "function": {
            "name": "get_roast",
            "description": "Get a roast of a wallet address",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {"type": "string"}
                },
                "required": ["wallet_address"],
                "additionalProperties": False,
            },
        },
    }
]

def get_sell_nft_batch_post(nft_batch):
    filtered_batch = []
    for nft in nft_batch:
        filtered_nft = {
            'received_timestamp': nft.get('timestamp', ''),
            'analysis_text': nft.get('analysis_text', ''),
            'decision_reason': nft.get('decision_reason', ''),
            'floor_price_in_eth': nft.get('floor_price', 0),
            'sender_address': nft.get('sender_address', ''),
            'network': nft.get('network', ''),
            'contract_address': nft.get('contract_address', ''), 
            'token_id': nft.get('token_id', ''),
            'total_score': nft.get('total_score', ''),
            'listing_type': nft.get('listing_type', ''),
            'opensea_url': nft.get('opensea_url', '')
        }
        filtered_batch.append(filtered_nft)

    # Split NFTs into listed and auctioned batches
    nfts_listed = [nft for nft in filtered_batch if nft['listing_type'] == 'LISTED']
    nfts_auctioned = [nft for nft in filtered_batch if nft['listing_type'] == 'AUCTIONED']

    # Convert to strings
    nfts_listed_str = json.dumps(nfts_listed, indent=2) if nfts_listed else "None"
    nfts_auctioned_str = json.dumps(nfts_auctioned, indent=2) if nfts_auctioned else "None"

    system_prompt = get_sell_nft_batch_post_prompt(nfts_listed_str, nfts_auctioned_str, len(filtered_batch))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
    )
    return response.choices[0].message.content

def get_wallet_analysis_response(wallet_data, base64_image, tone, current_valuation):
    system_prompt, user_prompt = get_wallet_analysis_prompt(wallet_data, tone, current_valuation)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", 
             "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
    )

    return response.choices[0].message.content

def get_artto_rewards_post(selected_nfts, total_reward_points):
    system_prompt = get_artto_rewards_post_prompt(selected_nfts, total_reward_points)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
    )
    return response.choices[0].message.content

def get_summary_nft_post(rationale_posts, nft_batch_count):
    system_prompt = get_summary_nft_post_prompt(rationale_posts, nft_batch_count)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
    )
    return response.choices[0].message.content

def get_simple_analysis_summary_nft_post(nft_batch):
    nft_analyses = []
    for nft in nft_batch:
        analysis = {
            "analysis_text": nft.get("analysis_text", ""),
            "acquire_recommendation": nft.get("acquire_recommendation", False)
        }
        nft_analyses.append(analysis)
    nft_analyses_str = json.dumps(nft_analyses)
    system_prompt = get_simple_analysis_summary_nft_post_prompt(nft_analyses_str, len(nft_batch))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
    )
    return response.choices[0].message.content

def get_artto_promotion(nft_collection_value, length):
    system_prompt = get_artto_promotion_prompt(nft_collection_value, length)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
    )
    return response.choices[0].message.content

def identify_spam(tweet):
    system_prompt = get_spam_identification_prompt(tweet)
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
        response_format=SpamTweet
    )
    return response.choices[0].message.parsed


def adjust_weights(weights, nft_scores):
    system_prompt = get_adjust_weights_prompt(weights, nft_scores)

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", 
             "content": system_prompt},
        ],
        response_format=UpdateWeights
    )

    new_weights = response.choices[0].message.parsed

    return new_weights

async def get_nft_post(artwork_analysis, score_details):
    print("Running get_nft_post")

    decision = score_details["decision"]

    system_prompt = get_nft_post_prompt(artwork_analysis, decision)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt}
        ]
    )

    return response.choices[0].message.content

async def get_final_decision(artwork_analysis, nft_metadata, from_address, score_details = None):
    decision_reason = ""

    if score_details is None:
        response = await get_total_score(artwork_analysis)
        decision = response["decision"]
        decision_reason = response["decision_reason"]
    else:
        decision = score_details["decision"]
        decision_reason = score_details["decision_reason"]

    ens_name = get_ens_name(from_address)

    system_prompt = get_keep_or_sell_decision(artwork_analysis, nft_metadata, ens_name, decision, decision_reason)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", 
             "content": system_prompt}
        ],
        response_format=AcquireOrReject
    )

    final_decision = response.choices[0].message.parsed

    return final_decision


async def get_nft_analysis(metadata):
    pretty_metadata = json.dumps(metadata, indent=2)
    try:
        is_top_collection = await is_top_collection(metadata["collection_id"], time_period='30d')
    except:
        is_top_collection = False

    system_prompt = get_nft_analysis_prompt(pretty_metadata, is_top_collection)

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", 
             "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": metadata["image_small_url"]
                        }
                    }
                ]
            }
        ],
        response_format=ArtworkAnalysis
    )

    artwork_analysis = response.choices[0].message.parsed

    print("artwork_analysis: ", artwork_analysis)
    return artwork_analysis

async def get_image_opinion(cast_details):

    try:
        author_details = f"{cast_details['display_name']} ({cast_details['username']}) - BIOGRAPHY:{cast_details['bio']}"
        cast_text = f"{author_details}\n\nText:{cast_details['text']}"
    except:
        cast_text = f"Text:{cast_details['text']}"


    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", 
             "content": get_image_analysis_prompt(cast_text)},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": cast_details["image_url"]
                        }
                    }
                ]
            }
        ],
        response_format=ArtworkAnalysisImageOnly,
    )

    image_analysis = response.choices[0].message.parsed

    print("image_analysis: ", image_analysis)

    system_prompt = get_image_analysis_post_prompt(image_analysis)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt}
        ]
    )

    return response.choices[0].message.content


async def get_thoughts_on_trending_casts(trending_casts):

    system_prompt = get_thoughts_on_trending_casts_prompt()
    messages = [
        {"role": "system", 
        "content": system_prompt},
    ]

    for cast in trending_casts:
        messages.append({
            "role": "user",
            "content": f"Post: {cast['text']} - Author: {cast['author']}"
        })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500
    )
    return response.choices[0].message.content


async def get_trending_post(trending_collections_response):
    system_prompt = get_trending_nft_thoughts_prompt(trending_collections_response)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
                {"role": "system", 
                "content": system_prompt},
            ],
        max_tokens=500
    )
    return response.choices[0].message.content


async def get_reply(cast_details, post_params):

    try:
        author_details = f"{cast_details['display_name']} ({cast_details['username']}) - BIOGRAPHY:{cast_details['bio']}"
        cast_text = f"{author_details}\n\nText:{cast_details['text']}"
    except:
        cast_text = f"Text:{cast_details['text']}"

    if cast_details.get("image_url") or cast_details.get("url"):
        print("Generating image opinion")
        reply = await get_image_opinion(cast_details)
        return (reply, None, None)

    print("Generating reply to text-only cast")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", 
            "content": get_reply_guy_prompt(cast_text, post_params)},
        ],
        tools=tools,
        max_tokens=300
    )

    if response.choices[0].message.tool_calls:
        # Iterate through all tool calls
        for tool_call in response.choices[0].message.tool_calls:
            if tool_call.function.name == "get_nft_opinion":
                print("Tool call: ", tool_call)
                tool_input = json.loads(tool_call.function.arguments)
                network = tool_input["network"]
                contract_address = tool_input["contract_address"]
                token_id = tool_input["token_id"]

                metadata = None

                try:
                    response = await get_artwork_analysis_and_metadata(network, contract_address, token_id)
                    artwork_analysis = response["artwork_analysis"]
                    metadata = response["metadata"]
                except Exception as e:
                    raise ValueError(f"Failed to fetch NFT metadata: {str(e)}")

                nft_details = {
                    "artwork_analysis": artwork_analysis,
                    "image_small_url": metadata["image_small_url"],
                    "chain": network,
                    "contract_address": contract_address,
                    "token_id": token_id,
                    "metadata": metadata
                }

                score_details = await get_total_score(artwork_analysis, nft_details)

                post = await get_nft_post(artwork_analysis, score_details)

                return (post, nft_details, score_details)
            
            if tool_call.function.name == "get_roast":
                print("Tool call: ", tool_call)
                tool_input = json.loads(tool_call.function.arguments)
                print("Tool input: ", tool_input)
                wallet_data = get_wallet_info(tool_input["wallet_address"])
                current_valuation = get_wallet_valuation(tool_input["wallet_address"])

                tone_default = 3
                response = get_analysis_params(wallet_data, tone_default, current_valuation)
                os.remove(response["temp_image_path"])
                analysis = get_wallet_analysis_response(wallet_data, response["base64_image"], tone_default, current_valuation)

                return (analysis, None, None)

    return (response.choices[0].message.content, None, None)

async def get_scheduled_post(post_type, post_params, previous_posts="No recent posts", additional_context="None"):
    system_prompt = get_scheduled_post_prompt(post_type, post_params, previous_posts, additional_context)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
                {"role": "system", 
                "content": system_prompt},
            ],
        max_tokens=300
    )
    return response.choices[0].message.content


async def main():
    # pass
    
    response, scores = await get_reply("hey @artto_ai - can you share your thoughts on this NFT? https://opensea.io/assets/ethereum/0xe70659b717112ac4e14284d0db2f5d5703df8e43/347")
    print(response)

    # response = await generate_reply_smart("yo @artto_ai would you buy this? https://basescan.org/nft/0x7d210dae7a88cadac22cefa9cb5baa4301b5c256/57")
    # print(response)

    # response = await generate_reply_smart("yo @artto_ai what kind of art do you like?")

    # print(response)



    # response = await get_nft_analysis("base", "0x7d210dae7A88Cadac22cEfa9cB5baA4301B5C256", "11")
    # print(response)
    # response = generate_image_reply({
    #     "text": "4. The Giving Tree @JohnKnopfPhotos",
    #     "url": "https://pbs.twimg.com/media/GdQCrG0XoAAttBL.jpg"
    # })
    # print(response)

if __name__ == "__main__":
    asyncio.run(main())