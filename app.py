import streamlit as st
import json
from google.cloud import bigquery
from google.oauth2 import service_account

# --- Page Config ---
st.set_page_config(page_title="BigQuery Explorer", layout="wide")
st.title("BigQuery Explorer & SQL Editor")

# --- File Uploader ---
with st.sidebar:
    st.header("Authentication")
    st.write("Upload your Service Account JSON key.")
    uploaded_file = st.file_uploader("Upload JSON", type=["json"])

if uploaded_file is not None:
    try:
        # 1. Parse JSON and Authenticate
        sa_info = json.load(uploaded_file)
        credentials = service_account.Credentials.from_service_account_info(sa_info)
        project_id = sa_info.get("project_id")
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        st.success(f"Authenticated successfully to project: **{project_id}**")
        
        # Fetch datasets once to use across tabs
        datasets = list(client.list_datasets())
        dataset_ids = [dataset.dataset_id for dataset in datasets] if datasets else []

        if not dataset_ids:
            st.warning("No datasets found in this project.")
        else:
            # --- Create Tabs ---
            tab1, tab2 = st.tabs(["📂 Schema Explorer", "⚡ Query Editor"])

            # ==========================================
            # TAB 1: SCHEMA EXPLORER
            # ==========================================
            with tab1:
                st.subheader("Explore Datasets and Tables")
                selected_dataset_id = st.selectbox("Select a Dataset", dataset_ids, key="explorer_dataset")
                
                if selected_dataset_id:
                    dataset_ref = client.dataset(selected_dataset_id)
                    tables = list(client.list_tables(dataset_ref))
                    
                    if not tables:
                        st.info(f"No tables found in '{selected_dataset_id}'.")
                    else:
                        table_ids = [{"Table Name": table.table_id} for table in tables]
                        st.dataframe(table_ids, use_container_width=True)

            # ==========================================
            # TAB 2: QUERY EDITOR
            # ==========================================
            with tab2:
                st.subheader("Run SQL Queries")
                
                # --- Query Builder Dropdowns ---
                st.markdown("Use the dropdowns below to help build your query context:")
                col1, col2 = st.columns(2)
                
                with col1:
                    q_dataset = st.selectbox("1. Select Dataset", dataset_ids, key="query_dataset")
                
                with col2:
                    if q_dataset:
                        # Fetch tables for the selected dataset
                        q_dataset_ref = client.dataset(q_dataset)
                        q_tables = list(client.list_tables(q_dataset_ref))
                        q_table_ids = [t.table_id for t in q_tables]
                        
                        q_table = st.selectbox("2. Select Table", q_table_ids, key="query_table")
                
                # --- Display fully qualified name and text area ---
                if q_dataset and q_table:
                    # Construct the exact table path needed for BigQuery
                    full_table_path = f"`{project_id}.{q_dataset}.{q_table}`"
                    st.info(f"**Target Table:** {full_table_path}")
                    
                    # Pre-fill the SQL editor with a basic query using the selected table
                    default_query = f"SELECT * \nFROM {full_table_path}"
                else:
                    default_query = "SELECT * FROM `project.dataset.table` LIMIT 10"

                # SQL Text Area
                query_input = st.text_area("Write your SQL query:", value=default_query, height=150)
                
                # --- Execute Query ---
                if st.button("Run Query", type="primary"):
                    if not query_input.strip():
                        st.warning("Please enter a SQL query.")
                    else:
                        with st.spinner("Executing query..."):
                            try:
                                # Run the query and convert directly to a Pandas DataFrame
                                query_job = client.query(query_input)
                                df = query_job.to_dataframe()
                                
                                st.success("Query executed successfully!")
                                st.write(f"**Results:** ({len(df)} rows)")
                                st.dataframe(df, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error executing query: {e}")

    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid service account key.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
