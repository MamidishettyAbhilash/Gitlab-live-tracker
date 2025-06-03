import streamlit as st
import requests
from collections import defaultdict
import datetime
import matplotlib.pyplot as plt

TOKEN = st.secrets["gitlab"]["token"]
BASE_URL = st.secrets["gitlab"]["base_url"]
HEADERS = {"Private-Token": TOKEN}

st.set_page_config(layout="wide", page_title="User Activity Details")
st.title("📊 User Activity Details")

# Sidebar filter options
st.sidebar.header("🔍 Filters")
show_commits = st.sidebar.checkbox("Show Commits", value=True)
show_merges = st.sidebar.checkbox("Show Merge Requests", value=True)
show_issues = st.sidebar.checkbox("Show Issues", value=True)

user_id = st.session_state.get('selected_user_id', None)

if not user_id:
    st.error("❌ User not selected. Go back and select a user.")
    st.stop()

# Get user info
user_res = requests.get(f"{BASE_URL}/users/{user_id}", headers=HEADERS)
if user_res.status_code != 200:
    st.error("Failed to fetch user details.")
    st.stop()
user = user_res.json()

st.header(f"👤 {user['name']} ({user['username']})")
st.markdown(f"[🔗 View Profile]({user['web_url']})")

# Fetch projects
projects_res = requests.get(f"{BASE_URL}/users/{user_id}/projects", headers=HEADERS)
if projects_res.status_code != 200:
    st.error("Failed to fetch projects.")
    st.stop()
projects = projects_res.json()

if not projects:
    st.warning("No projects found.")
    st.stop()

for project in projects:
    st.subheader(f"📁 {project['name']} (ID: {project['id']})")

    # --- Preview README.md content ---
    readme_url = f"{BASE_URL}/projects/{project['id']}/repository/files/README.md/raw?ref=main"
    readme_res = requests.get(readme_url, headers=HEADERS)
    if readme_res.status_code == 200:
        readme_text = readme_res.text
        preview = "\n".join(readme_text.splitlines()[:10])  # first 10 lines
        st.markdown(f"**📄 README.md Preview:**\n```\n{preview}\n```")
    else:
        st.markdown("**📄 README.md not found or inaccessible on branch 'main'.**")

    # Prepare data containers
    commits = []
    merge_requests = []
    issues = []

    # Fetch commits
    if show_commits:
        page = 1
        while True:
            commits_url = f"{BASE_URL}/projects/{project['id']}/repository/commits"
            params = {"per_page": 100, "page": page}
            res = requests.get(commits_url, headers=HEADERS, params=params)
            if res.status_code != 200 or not res.json():
                break
            data = res.json()
            commits.extend([c for c in data if c.get("author_name", "").lower() == user["name"].lower()])
            page += 1

    # Fetch merge requests
    if show_merges:
        mr_url = f"{BASE_URL}/projects/{project['id']}/merge_requests"
        mr_res = requests.get(mr_url, headers=HEADERS, params={"author_id": user_id, "state": "all"})
        if mr_res.status_code == 200:
            merge_requests = mr_res.json()

    # Fetch issues
    if show_issues:
        issues_url = f"{BASE_URL}/projects/{project['id']}/issues"
        issues_res = requests.get(issues_url, headers=HEADERS, params={"author_id": user_id, "state": "all"})
        if issues_res.status_code == 200:
            issues = issues_res.json()

    # Show counts
    st.markdown(f"**Summary:** Commits: {len(commits)} | Merge Requests: {len(merge_requests)} | Issues: {len(issues)}")

    # Use tabs to show details
    tabs = st.tabs(["Commits", "Merge Requests", "Issues"])

    with tabs[0]:
        if not show_commits:
            st.info("Commits view is disabled by sidebar filter.")
        elif commits:
            commits_by_date = defaultdict(list)

            for c in commits:
                date = c["created_at"][:10]
                title = c["title"]
                message = c.get("message", "")
                commits_by_date[date].append((title, message))


            for date, messages in sorted(commits_by_date.items()):
                st.markdown(f"📅 **{date}**")
                for title, msg in messages:
                    st.markdown(f"- **Title:** {title}")
                    st.markdown(f"  \t📝 **Message:** `{msg.strip()}`")

            dates = list(commits_by_date.keys())
            counts = [len(msgs) for msgs in commits_by_date.values()]
            dates_dt = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates]


            plt.figure(figsize=(10, 3))
            plt.bar(dates_dt, counts, color='skyblue')
            plt.title("Commits per Day")
            plt.xlabel("Date and Time")
            plt.ylabel("Number of Commits")
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(plt)
        else:
            st.write("No commits found.")

    with tabs[1]:
        if not show_merges:
            st.info("Merge Requests view is disabled by sidebar filter.")
        elif merge_requests:
            for mr in merge_requests:
                st.markdown(f"- [{mr['title']}]({mr['web_url']}) (State: {mr['state']}, Created: {mr['created_at'][:10]})")
        else:
            st.write("No merge requests found.")

    with tabs[2]:
        if not show_issues:
            st.info("Issues view is disabled by sidebar filter.")
        elif issues:
            for issue in issues:
                st.markdown(f"- [{issue['title']}]({issue['web_url']}) (State: {issue['state']}, Created: {issue['created_at'][:10]})")
        else:
            st.write("No issues found.")

    # Branches and files
    st.markdown("🌿 **Branches:**")
    branches_res = requests.get(f"{BASE_URL}/projects/{project['id']}/repository/branches", headers=HEADERS)
    if branches_res.status_code == 200:
        branches = branches_res.json()
        for branch in branches:
            st.markdown(f"🔸 `{branch['name']}`")

            tree_url = f"{BASE_URL}/projects/{project['id']}/repository/tree"
            tree_res = requests.get(tree_url, headers=HEADERS, params={"ref": branch['name']})
            if tree_res.status_code == 200:
                files = tree_res.json()
                for f in files:
                    link_url = f"https://code.swecha.org/{project['path_with_namespace']}/-/tree/{branch['name']}/{f['path']}" if f['type'] == 'tree' else f"https://code.swecha.org/{project['path_with_namespace']}/-/blob/{branch['name']}/{f['path']}"
                    icon = "📁" if f['type'] == 'tree' else "📄"
                    st.markdown(f"{icon} [{f['name']}]({link_url})")
            else:
                st.write("Unable to fetch files for branch.")
    else:
        st.write("No branches found.")
