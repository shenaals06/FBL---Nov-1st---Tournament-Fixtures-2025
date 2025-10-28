import streamlit as st
import pandas as pd
import io
import base64

st.set_page_config(page_title="Multi-Age Group Soccer Tournament", layout="wide")
st.title("Multi-Age Group Soccer Tournament Manager")

# --- Initialize session state ---
if 'matches_data' not in st.session_state:
    st.session_state['matches_data'] = {}
if 'standings_data' not in st.session_state:
    st.session_state['standings_data'] = {}
if 'finals_data' not in st.session_state:
    st.session_state['finals_data'] = {}
if 'teams_data' not in st.session_state:
    st.session_state['teams_data'] = {}

# --- Age Groups Setup ---
st.sidebar.header("Tournament Setup")
age_groups_input = st.sidebar.text_area(
    "Enter Age Groups (comma separated, e.g., U10,U12,U14)", "U10,U12")
age_groups = [ag.strip() for ag in age_groups_input.split(',') if ag.strip()]

# --- Tabs for Organizer and Participant Mode ---
tab1, tab2 = st.tabs(["Organizer", "Participant"])

# --- Organizer Mode ---
with tab1:
    st.subheader("Organizer Mode")
    password = st.text_input("Enter Organizer Password", type="password")
    organizer_password = "FBL123"  # Replace with your secure password
    if password == organizer_password:
        st.success("Access granted! You can now manage the tournament.")

        for selected_age_group in age_groups:
            st.markdown(f"### {selected_age_group} Tournament")

            # Teams and Format
            st.subheader(f"{selected_age_group} Setup")
            num_teams = st.number_input(
                f"Number of Teams for {selected_age_group}", min_value=6, max_value=16, value=6, step=1,
                key=f"num_{selected_age_group}")
            format_options = ['Single Group League', 'Two Groups with Top 2 to Final']
            tournament_format = st.selectbox(
                f"Select Tournament Format for {selected_age_group}", format_options,
                key=f"format_{selected_age_group}")

            # Team Names
            st.subheader(f"Enter Team Names for {selected_age_group}")
            teams = []
            for i in range(num_teams):
                t = st.text_input(f"Team {i+1}", f"Team {i+1}",
                                  key=f"{selected_age_group}_team_{i}")
                teams.append(t)
            st.session_state['teams_data'][selected_age_group] = teams

            # Generate Matches
            def generate_matches(teams, format_type):
                matches = []
                match_id = 1
                if format_type == 'Single Group League':
                    for i in range(len(teams)):
                        for j in range(i + 1, len(teams)):
                            matches.append({'Match ID': match_id, 'Team A': teams[i], 'Team B': teams[j],
                                            'Score A': 0, 'Score B': 0})
                            match_id += 1
                    return {'Group 1': pd.DataFrame(matches)}
                elif format_type == 'Two Groups with Top 2 to Final':
                    mid = len(teams) // 2
                    group1 = teams[:mid]
                    group2 = teams[mid:]

                    def round_robin(group, start_id):
                        ms = []
                        m_id = start_id
                        for i in range(len(group)):
                            for j in range(i + 1, len(group)):
                                ms.append({'Match ID': m_id, 'Team A': group[i], 'Team B': group[j],
                                           'Score A': 0, 'Score B': 0})
                                m_id += 1
                        return pd.DataFrame(ms)

                    return {'Group 1': round_robin(group1, 1), 'Group 2': round_robin(group2, 100)}

            matches_groups = generate_matches(teams, tournament_format)

            # Display & Edit Matches
            st.subheader(f"{selected_age_group} Matches")
            edited_matches = {}
            for g_name, df in matches_groups.items():
                with st.expander(f"{g_name}"):
                    rows = []
                    for idx, row in df.iterrows():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"Match {int(row['Match ID'])}: {row['Team A']} vs {row['Team B']}")
                        with col2:
                            sa = st.number_input(f"Score A_{int(row['Match ID'])}", 0, 50, int(row['Score A']),
                                                 key=f"{selected_age_group}_{g_name}_sa_{int(row['Match ID'])}")
                        with col3:
                            sb = st.number_input(f"Score B_{int(row['Match ID'])}", 0, 50, int(row['Score B']),
                                                 key=f"{selected_age_group}_{g_name}_sb_{int(row['Match ID'])}")
                        rows.append({'Match ID': row['Match ID'], 'Team A': row['Team A'], 'Team B': row['Team B'],
                                     'Score A': sa, 'Score B': sb})
                    edited_matches[g_name] = pd.DataFrame(rows)
                    st.dataframe(edited_matches[g_name])

            st.session_state['matches_data'][selected_age_group] = edited_matches

            # Compute Standings
            def compute_standings(df):
                teams_list = list(set(df['Team A']).union(set(df['Team B'])))
                standings = pd.DataFrame({'Team': teams_list, 'Played': 0, 'Won': 0, 'Drawn': 0,
                                          'Lost': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Points': 0})
                standings = standings.set_index('Team')
                for _, m in df.iterrows():
                    tA, tB = m['Team A'], m['Team B']
                    sA, sB = int(m['Score A']), int(m['Score B'])
                    standings.at[tA, 'Played'] += 1
                    standings.at[tB, 'Played'] += 1
                    standings.at[tA, 'GF'] += sA
                    standings.at[tA, 'GA'] += sB
                    standings.at[tB, 'GF'] += sB
                    standings.at[tB, 'GA'] += sA
                    if sA > sB:
                        standings.at[tA, 'Won'] += 1
                        standings.at[tA, 'Points'] += 3
                        standings.at[tB, 'Lost'] += 1
                    elif sB > sA:
                        standings.at[tB, 'Won'] += 1
                        standings.at[tB, 'Points'] += 3
                        standings.at[tA, 'Lost'] += 1
                    else:
                        standings.at[tA, 'Drawn'] += 1
                        standings.at[tB, 'Drawn'] += 1
                        standings.at[tA, 'Points'] += 1
                        standings.at[tB, 'Points'] += 1
                standings['GD'] = standings['GF'] - standings['GA']
                standings = standings.sort_values(by=['Points', 'GD', 'GF'], ascending=[False, False, False]).reset_index()
                standings.index += 1  # Start ranking from 1
                return standings

            st.subheader(f"{selected_age_group} Standings")
            standings_groups = {}
            for g_name, df in edited_matches.items():
                with st.expander(f"Standings {g_name}"):
                    standings_groups[g_name] = compute_standings(df)
                    st.table(standings_groups[g_name])

            st.session_state['standings_data'][selected_age_group] = standings_groups

            # Final
            st.subheader(f"{selected_age_group} Final")
            if tournament_format == 'Single Group League':
                finalist1, finalist2 = standings_groups['Group 1'].iloc[0]['Team'], standings_groups['Group 1'].iloc[1]['Team']
            else:
                finalist1, finalist2 = standings_groups['Group 1'].iloc[0]['Team'], standings_groups['Group 2'].iloc[0]['Team']
            st.markdown(f"Finalists: {finalist1} vs {finalist2}")
            final_score_a = st.number_input(f"Final Score {finalist1}", 0, 50, 0,
                                            key=f"final_{selected_age_group}_a")
            final_score_b = st.number_input(f"Final Score {finalist2}", 0, 50, 0,
                                            key=f"final_{selected_age_group}_b")
            final_winner = finalist1 if final_score_a > final_score_b else finalist2 if final_score_b > final_score_a else 'Draw'
            st.markdown(f"**Winner: {final_winner}**")
            st.session_state['finals_data'][selected_age_group] = {'Finalist 1': finalist1,
                                                                  'Finalist 2': finalist2,
                                                                  'Score 1': final_score_a,
                                                                  'Score 2': final_score_b,
                                                                  'Winner': final_winner}

        # Export Excel
        st.header("Export All Age Groups to Excel")
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            for ag in age_groups:
                for g_name, df in st.session_state['matches_data'][ag].items():
                    df.to_excel(writer, sheet_name=f'{ag}_{g_name}_Matches', index=False)
                for g_name, df in st.session_state['standings_data'][ag].items():
                    df.to_excel(writer, sheet_name=f'{ag}_{g_name}_Standings', index=False)
                pd.DataFrame([st.session_state['finals_data'][ag]]).to_excel(writer, sheet_name=f'{ag}_Final', index=False)
        excel_bytes = excel_buffer.getvalue()
        b64 = base64.b64encode(excel_bytes).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="all_age_groups_tournament.xlsx">Download Excel</a>', unsafe_allow_html=True)

    else:
        st.warning("Enter the correct password to access organizer mode.")

# --- Participant Mode ---
with tab2:
    st.subheader("Participant Mode (Read-Only)")
    for selected_age_group in age_groups:
        st.markdown(f"### {selected_age_group} Tournament")
        teams = st.session_state['teams_data'].get(selected_age_group, [])
        if teams:
            selected_teams = st.multiselect(f"Select your team(s) for {selected_age_group}", teams,
                                            key=f"participant_{selected_age_group}")
            if selected_teams:
                # Matches
                all_matches = pd.concat(st.session_state['matches_data'].get(selected_age_group, {}).values(),
                                        ignore_index=True)
                filtered_matches = all_matches[(all_matches['Team A'].isin(selected_teams)) | (all_matches['Team B'].isin(selected_teams))]
                with st.expander("Matches"):
                    st.dataframe(filtered_matches)

                # Standings
                all_standings = pd.concat(st.session_state['standings_data'].get(selected_age_group, {}).values(),
                                          ignore_index=True)
                filtered_standings = all_standings[all_standings['Team'].isin(selected_teams)]
                with st.expander("Standings"):
                    st.table(filtered_standings)

                # Final
                final_info = st.session_state['finals_data'].get(selected_age_group, {})
                if final_info and any(t in selected_teams for t in [final_info.get('Finalist 1'), final_info.get('Finalist 2')]):
                    st.markdown(f"**Final:** {final_info['Finalist 1']} ({final_info['Score 1']}) vs {final_info['Finalist 2']} ({final_info['Score 2']})")
                    st.markdown(f"**Winner:** {final_info['Winner']}")
