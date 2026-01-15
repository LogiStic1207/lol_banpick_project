"""
Streamlit-based UI for the LoL ban/pick assistant
===============================================

This module provides a simple web-based user interface built with
Streamlit.  It allows users to:

1. Input a list of summoner names and taglines to analyse using the
   Riot API (via functions in `riot_api_skeleton.py`).
2. Upload or load local scrim data from the `data/` folder.  The
   scrim data is expected to be stored in an Excel file with a
   sheet called "스크림 데이터" and columns such as 경기에 기록된
   챔피언, 밴, 결과 등을 포함합니다.
3. View aggregated champion usage statistics from both the Riot API
   and the scrim data, and combine them with adjustable weights to
   inform ban/pick recommendations.

To run this UI locally:

```
streamlit run src/app.py
```

Make sure you have installed the dependencies listed in
`requirements.txt` (including `streamlit`) and have set your
`RIOT_API_KEY` in a `.env` file at the project root.  The UI will
open in your default web browser.

Note: This is a skeleton implementation.  You will need to fill
in the analysis and recommendation logic according to your needs.
"""

from __future__ import annotations

import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from typing import List, Tuple

from riot_api_skeleton import get_puuid, summarise_champion_usage, QUEUE_IDS


def load_scrim_data(file_path: str) -> pd.DataFrame:
    """Load scrim data from an Excel file.

    The file must contain a sheet named "스크림 데이터".  If the file
    cannot be read or the sheet does not exist, an empty DataFrame
    will be returned.

    Args:
        file_path: Path to the Excel file relative to the project root.

    Returns:
        A Pandas DataFrame containing the scrim data.
    """
    try:
        xls = pd.ExcelFile(file_path)
        if "스크림 데이터" in xls.sheet_names:
            return pd.read_excel(xls, sheet_name="스크림 데이터")
        else:
            st.warning(f"Sheet '스크림 데이터' not found in {file_path}")
    except Exception as e:
        st.error(f"Failed to load scrim data: {e}")
    return pd.DataFrame()


def display_scrim_summary(df: pd.DataFrame) -> None:
    """Display a summary of scrim data in the Streamlit app.

    This function aggregates champion usage and win rates from the
    provided DataFrame and displays them in tabular form.  It
    distinguishes between our team's picks and the opponent's picks.

    Args:
        df: DataFrame containing scrim data.
    """
    if df.empty:
        st.info("No scrim data available.")
        return

    st.subheader("스크림 데이터 요약")
    # Our team picks
    our_picks = pd.concat(
        [df["탑"], df["정글"], df["미드"], df["원딜"], df["서폿"]]
    ).rename("champion")
    our_counts = our_picks.value_counts().reset_index()
    our_counts.columns = ["champion", "games"]
    st.write("**우리팀 챔피언 사용 빈도**")
    st.dataframe(our_counts)

    # Opponent picks
    opp_picks = pd.concat(
        [df["탑.1"], df["정글.1"], df["미드.1"], df["원딜.1"], df["서폿.1"]]
    ).rename("champion")
    opp_counts = opp_picks.value_counts().reset_index()
    opp_counts.columns = ["champion", "games"]
    st.write("**상대팀 챔피언 사용 빈도**")
    st.dataframe(opp_counts)

    # Win rate by champion for our team
    win_rate_df = (
        df[["탑", "정글", "미드", "원딜", "서폿", "승"]]
        .melt(id_vars="승", value_vars=["탑", "정글", "미드", "원딜", "서폿"],
              value_name="champion", var_name="position")
    )
    win_rate_summary = (
        win_rate_df.groupby("champion")["승"]
        .agg(["count", "sum"])
        .rename(columns={"count": "games", "sum": "wins"})
    )
    win_rate_summary["win_rate"] = win_rate_summary["wins"] / win_rate_summary["games"]
    win_rate_summary = win_rate_summary.reset_index().sort_values(
        by=["games", "win_rate"], ascending=[False, False]
    )
    st.write("**우리팀 스크림 승률**")
    st.dataframe(win_rate_summary)


def run_analysis(players: List[Tuple[str, str]], queues: List[int], max_matches: int) -> List[Tuple[str, pd.DataFrame]]:
    """Fetch champion usage statistics for a list of players via the Riot API.

    Args:
        players: List of (summoner_name, tag) tuples.
        queues: Queue IDs to include.
        max_matches: Number of matches to analyse per queue.

    Returns:
        A list of tuples (player_identifier, DataFrame) where each DataFrame
        contains the champion usage statistics for that player.
    """
    results = []
    for name, tag in players:
        if not name or not tag:
            continue
        try:
            puuid = get_puuid(name, tag)
            df = summarise_champion_usage(puuid, queues, max_matches_per_queue=max_matches)
            results.append((f"{name}#{tag}", df))
        except Exception as e:
            results.append((f"{name}#{tag}", pd.DataFrame()))
            st.error(f"Failed to analyse {name}#{tag}: {e}")
    return results


def main() -> None:
    """Entry point for the Streamlit app."""
    # Load environment variables (including RIOT_API_KEY)
    load_dotenv()
    st.set_page_config(page_title="LoL Ban/Pick Assistant", layout="wide")
    st.title("LoL 밴픽 추천 도우미")

    # Sidebar: Player inputs
    st.sidebar.header("플레이어 분석 설정")
    num_players = st.sidebar.number_input("분석할 소환사 수", min_value=1, max_value=10, value=3)
    player_inputs: List[Tuple[str, str]] = []
    for i in range(int(num_players)):
        name = st.sidebar.text_input(f"소환사{i+1} 이름", key=f"name_{i}")
        tag = st.sidebar.text_input(f"소환사{i+1} 태그", key=f"tag_{i}")
        player_inputs.append((name.strip(), tag.strip()))

    # Sidebar: Queue selection
    st.sidebar.header("큐 타입 선택")
    include_ranked_solo = st.sidebar.checkbox("Ranked Solo/Duo", value=True)
    include_ranked_flex = st.sidebar.checkbox("Ranked Flex", value=True)
    include_normal = st.sidebar.checkbox("Normal", value=True)
    queues: List[int] = []
    if include_ranked_solo:
        queues.append(QUEUE_IDS["RANKED_SOLO"])
    if include_ranked_flex:
        queues.append(QUEUE_IDS["RANKED_FLEX"])
    if include_normal:
        queues.append(QUEUE_IDS["NORMAL"])
    max_matches = int(st.sidebar.slider("큐별 최대 분석 경기수", min_value=5, max_value=30, value=15))

    # Sidebar: Scrim data file selection or upload
    st.sidebar.header("스크림 데이터")
    scrim_files = [f for f in os.listdir("data") if f.lower().endswith((".xlsx", ".xls"))]
    selected_scrim_file = st.sidebar.selectbox(
        "데이터/ 폴더 내 스크림 파일 선택", options=["(없음)"] + scrim_files
    )
    uploaded_scrim = st.sidebar.file_uploader("스크림 데이터 업로드 (.xlsx)", type=["xlsx", "xls"])

    # Run analysis when button is pressed
    if st.sidebar.button("분석 실행"):
        # Analyse Riot API data
        st.subheader("Riot API 데이터 분석 결과")
        results = run_analysis(player_inputs, queues, max_matches)
        for summoner, df in results:
            st.write(f"### {summoner}")
            if df.empty:
                st.write("No data available or failed to fetch.")
            else:
                st.dataframe(df)

        # Load and display scrim data
        scrim_df = pd.DataFrame()
        if uploaded_scrim is not None:
            # Use uploaded file
            try:
                scrim_df = pd.read_excel(uploaded_scrim, sheet_name="스크림 데이터")
            except Exception as e:
                st.error(f"Failed to read uploaded file: {e}")
        elif selected_scrim_file != "(없음)":
            scrim_path = os.path.join("data", selected_scrim_file)
            scrim_df = load_scrim_data(scrim_path)

        if not scrim_df.empty:
            display_scrim_summary(scrim_df)
        else:
            st.info("스크림 데이터를 로드하지 않았거나, 데이터가 없습니다.")

    else:
        st.info("왼쪽 패널에서 설정을 선택하고 '분석 실행'을 눌러 주세요.")


if __name__ == "__main__":
    main()