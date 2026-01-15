"""
Riot API data collection skeleton
================================

This script demonstrates how to automate the retrieval of recent match data
for a set of League of Legends summoners using Riot's official REST API.
It shows how to:

1. Load your Riot API key from an environment variable or configuration file.
2. Resolve each player's account name and tag to a unique summoner ID.
3. Fetch a list of recent match IDs for the chosen queue types (e.g. ranked
   solo/duo, ranked flex, normal).  Queue IDs are specified by Riot and can
   be found in the official documentation.
4. Loop through match histories to compute aggregate statistics such as the
   number of games played on each champion and win rates.

NOTE:
  - This script does not handle rate limiting or retries.  When building a
    production-quality tool you should add logic to respect the Riot API's
    rate limits and handle transient network errors gracefully.
  - For brevity, exception handling has been kept minimal.  You may wish to
    add more robust error handling depending on your needs.

Usage:
  1. Install dependencies: `pip install requests pandas` (and optionally
     python-dotenv if you want to load keys from a `.env` file).
  2. Set the RIOT_API_KEY environment variable to your personal Riot API key.
  3. Define the list of players (as tuples of summoner name and tag) you
     wish to analyse under `PLAYERS`.
  4. Run the script in a Python environment (Jupyter notebook, VSCode or
     command line) to produce a Pandas DataFrame summarising champion usage.
"""

import os
import time
from typing import List, Dict, Tuple, Optional
import requests
import pandas as pd

# Base endpoints for the Riot API.  Use the appropriate regional routing
# (e.g. asia, americas, europe) depending on the players' region.  For
# Korea, matches are served from the `asia` server.  See Riot docs for
# details: https://developer.riotgames.com/docs/lol
REGIONAL_RIOT_ENDPOINT = "https://asia.api.riotgames.com"  # for match endpoints
LOCAL_RIOT_ENDPOINT = "https://kr.api.riotgames.com"       # for summoner endpoints

# Load your Riot API key from the environment.  You can also hardcode
# this string here, but keep in mind that sharing your API key publicly
# violates Riot's terms of service.
API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    raise RuntimeError("RIOT_API_KEY environment variable not set.\n"
                       "Visit https://developer.riotgames.com/ to register for an API key and set it in your environment.")

# HTTP headers including the API key.  All Riot API requests must include
# an X-Riot-Token header.
HEADERS = {
    "X-Riot-Token": API_KEY
}

# Supported queue types.  See https://static.developer.riotgames.com/docs/lol/queues.json
# for a full list.  Common ones include:
#  420: Ranked Solo/Duo
#  440: Ranked Flex
#  430: Normal Blind Pick
#  450: ARAM (to be filtered out later)
QUEUE_IDS = {
    "RANKED_SOLO": 420,
    "RANKED_FLEX": 440,
    "NORMAL": 430,
}

def get_puuid(summoner_name: str, tagline: str) -> str:
    """Resolve a Riot ID (name#tagline) to a PUUID using the Riot account-v1 API.

    Args:
        summoner_name: The in-game summoner name (before the '#').
        tagline: The tagline (after the '#', e.g. KR1).

    Returns:
        The player's globally unique PUUID.

    Raises:
        HTTPError: If the API call fails.
    """
    url = f"{REGIONAL_RIOT_ENDPOINT}/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    return data["puuid"]


def get_match_ids(puuid: str, start: int = 0, count: int = 20, queue: Optional[int] = None) -> List[str]:
    """Retrieve a list of recent match IDs for a given player.

    Args:
        puuid: Player's PUUID obtained from get_puuid.
        start: Index to start fetching matches from (0 is most recent).
        count: Number of match IDs to retrieve (max 100 per request).
        queue: Optional queue ID to filter matches (e.g. 420 for ranked solo).

    Returns:
        A list of match IDs.
    """
    params = {
        "start": start,
        "count": count,
    }
    if queue is not None:
        params["queue"] = queue
    url = f"{REGIONAL_RIOT_ENDPOINT}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def get_match_details(match_id: str) -> Dict:
    """Retrieve the full match details for a given match ID.

    Args:
        match_id: The unique match identifier (e.g. KR_1234567890).

    Returns:
        A dictionary with match details including participants and their stats.
    """
    url = f"{REGIONAL_RIOT_ENDPOINT}/lol/match/v5/matches/{match_id}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def summarise_champion_usage(puuid: str, queue_ids: List[int], max_matches_per_queue: int = 20) -> pd.DataFrame:
    """Aggregate champion usage statistics for the given PUUID across multiple queues.

    This function fetches up to `max_matches_per_queue` recent matches for each queue ID,
    then builds a Pandas DataFrame summarising how often each champion was played and
    the corresponding win rate.

    Args:
        puuid: Player's PUUID.
        queue_ids: List of queue IDs to include.
        max_matches_per_queue: Max number of matches to analyse per queue.

    Returns:
        A Pandas DataFrame with columns [champion, games, wins, losses, win_rate].
    """
    usage: Dict[str, Dict[str, int]] = {}

    for qid in queue_ids:
        try:
            match_ids = get_match_ids(puuid, count=max_matches_per_queue, queue=qid)
        except requests.HTTPError as e:
            print(f"Failed to fetch matches for queue {qid}: {e}")
            continue
        # Loop through each match and tally champion usage
        for mid in match_ids:
            try:
                match = get_match_details(mid)
            except requests.HTTPError as e:
                print(f"Failed to fetch match {mid}: {e}")
                continue
            # Extract the participant corresponding to this PUUID
            participants = match["info"]["participants"]
            player_data = next((p for p in participants if p["puuid"] == puuid), None)
            if not player_data:
                continue
            champ = player_data["championName"]
            win = 1 if player_data.get("win") else 0
            # Initialise stats if not already present
            if champ not in usage:
                usage[champ] = {"games": 0, "wins": 0, "losses": 0}
            usage[champ]["games"] += 1
            usage[champ]["wins"] += win
            usage[champ]["losses"] += 1 - win
            # Respect rate limits by sleeping briefly between calls
            time.sleep(0.2)

    # Convert to DataFrame
    rows = []
    for champ, stats in usage.items():
        games = stats["games"]
        wins = stats["wins"]
        losses = stats["losses"]
        win_rate = wins / games if games > 0 else 0
        rows.append({
            "champion": champ,
            "games": games,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
        })
    df = pd.DataFrame(rows)
    return df.sort_values(by=["games", "win_rate"], ascending=[False, False]).reset_index(drop=True)


def main() -> None:
    """Example usage of the helper functions above.

    Define the list of players you want to analyse and print out a summary
    of their champion usage across the desired queues.  Adjust the
    `PLAYERS` list and `queue_ids` variable as needed for your case.
    """
    # List of players as (summoner_name, tag)
    PLAYERS: List[Tuple[str, str]] = [
        ("구수어빵", "KR1"),
        ("이로리노", "KR1"),
        ("에잇기분이다", "KR1"),
    ]
    # Choose which queues to include (exclude ARAM).  You can modify this list.
    queues_to_fetch = [QUEUE_IDS["RANKED_SOLO"], QUEUE_IDS["RANKED_FLEX"], QUEUE_IDS["NORMAL"]]
    for name, tag in PLAYERS:
        try:
            puuid = get_puuid(name, tag)
        except requests.HTTPError as e:
            print(f"Failed to resolve {name}#{tag}: {e}")
            continue
        print(f"\n=== Champion usage for {name}#{tag} ===")
        df = summarise_champion_usage(puuid, queues_to_fetch, max_matches_per_queue=15)
        if df.empty:
            print("No match data available for the specified queues.")
        else:
            print(df.head(10))


if __name__ == "__main__":
    main()