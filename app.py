## Run with streamlit: streamlit run app.py





import streamlit as st
import yaml
from openai import OpenAI
import json
import pickle
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder,ColumnsAutoSizeMode
import report
import copy

# -------INIT VARIABLES----------
# initial openai messages
initial_dict_for_all_content_information = {"company_name": "N/A", "company_description": "N/A", "value_chain":{}}


system_prompt_chat = """
You act as an AI expert that helps companies to identify usefull Generative AI use cases. Always ask one single question at a time.
Collect the information in the following sequence:
- Start with a greating and how you can help
- Ask the user the company name.
- After you ask about a short description what the company is doing.
- After you should propose a value chain for the given company. This should be appropriate to the industry of the company. Present the value chain components in a table with columns "component name" and "component description" . Ask if this value chain is right for the company.
- Generate for each value chain component a Gen AI use case in one batch. Present the use case in one table with column "name", "component of value chain", "description"
- Ask if the user wants more idea.
- Example for a value chain in insurance is  product development, underwriting, marketing & sales, claims, IT , finance



"""
system_prompt_JSON_Delta = """
From last conversation, please extract and add the new information into the JSON. I you don't any new information, don't change the current state.

The json format is like this:
{
  "company_name": "<the name of the company, if not given by the user it's N/A>",
  "company_description": "<short description what is the company doing, if not given by the user it's N/A>"
  "value_chain":
    [
       {
        "name": "<name of this component>"
        "description": "<description of component>"
        "use_cases": [ 
            {
                "name": "<name of the use case>"
                "description": "<description of the use case>"
            }, 
        {},
        ...
        ]
    ]
}

The current state of the JSON is here:

"""

system_prompt_JSON = """
From our conversation, please extract information and provide it in a JSON format, as below.
Just provide information that exists in the conversation, don't generate new content. If there is no use cases, leave it empty.


{
  "company_name": "<the name of the compane, if not given by the user it's N/A>",
  "company_description": "<short description what is the company doing, if not given by the user it's N/A>"
  "value_chain":
    {
      "<name of first component>": {
        "description": "<description of component>"
        "use_cases": {
          "<use_case_name1>": {
            "description": "<description of the use case>"
          }, ...
        }
      },
      {..},
      ...,
      {}

    }
  ]

  }
}

"""





# -------INIT SESSION_STATE----------

# Variable to determine if chatbot is already initialized
if "initialized_chat" not in st.session_state:
    st.session_state.initialized_chat= False

# Initialize messages for OpenAI conversation
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": system_prompt_chat}]

# Json variable that we get back from open ai
if "open_ai_json_string" not in st.session_state:
    st.session_state.open_ai_json_string = initial_dict_for_all_content_information

# All content (without user details)
if "all_content_information" not in st.session_state:
    st.session_state.all_content_information = initial_dict_for_all_content_information

#List of all user details of the use cases (stored separately form "use_cases" to avoid overwriting)
if "use_cases_user_details" not in st.session_state:
    st.session_state.use_cases_user_details = {}

#Information to display in use case details ui
if "use_case_details_displayed" not in st.session_state:
    st.session_state.use_case_details_displayed = None

#variable for collecting error messages for debugging
if "error_messages" not in st.session_state:
    st.session_state.error_messages = []



# -------HELPLER FUNCTION----------
def string_to_json(intput_string):
    json_position = intput_string.find("{")

    if json_position != -1:
        json_substring = intput_string[json_position + 0:]
        try:
            json_data = json.loads(json_substring)
            return json_data
        except json.JSONDecodeError as e:
            st.warning("Error parsing JSON data:" + e.msg)
    else:
        debugger_container.write("The text 'JSON' was not found in the string.")
    return initial_dict_for_all_content_information

def show_use_cases_in_datails_UI(use_case, use_case_details_key):
    details={}
    details["name"]=use_case["name"]
    details["description"]=use_case["description"]
    details["dict_key"]=use_case_details_key
    st.session_state.use_case_details_displayed=details


# -------CREDENTIALS----------

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

try:
    with open("chatgpt_api_credentials.yml", 'r') as file:
        creds = yaml.safe_load(file)
except:
    creds = {}

# SIDEBAR
with st.sidebar:
    openai_api_key = creds.get("openai_key", '')
    if openai_api_key:
        st.text("OpenAI API Key Provided")
    else:
        openai_api_key = st.text_input("Please provide our OpenAI API Key")
        # Hyperlink
        "[Get an OpenAI API key](https://openai.com/blog/openai-api)"



if openai_api_key:
    # -------LAYOUT----------


    st.title("GenAI IdeaWorks")
    # st.title("💬 Chatbot")


    tab_chat, tab_dashboard, tab_session, tab_debugger = st.tabs(["💬 Chat", "📈 Dashboard", " 💾 Load/Save Session", "🧑‍🚒 Debugger"])
    # tab_chat.subheader("A tab with a chart")


    chatbot_container = tab_chat.container(border=True)

    company_container = tab_dashboard.expander("Company Information", expanded=True)
    # company_container.caption("Company Information")



    value_container = tab_dashboard.expander("Company's Value Chain", expanded=True)
    # value_container=st.container(border=True, height=300)
    # value_container.caption("Company's Value Chain")

    usecase_container = tab_dashboard.expander("UseCase List", expanded=True)



    details_container = tab_dashboard.expander("Use Case Details", expanded=True)


    session_container = tab_session.container()
    debugger_container = tab_debugger.container()
    # st.container(border=True, height=300)





    # -------CHATBOT CONTAINER----------


    # Initialize Open AI API
    if "open_ai_client" not in st.session_state:
        st.session_state.open_ai_client = OpenAI(api_key=openai_api_key)


    def open_ai_get_answer():
        # Get Answer from ChatGPT
        client = st.session_state.open_ai_client
        st.session_state.messages.append({"role": "user", "content": prompt})
        messages.chat_message("user").write(prompt)
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state.messages)
        msg = response.choices[0].message.content

        st.session_state.messages.append({"role": "assistant", "content": msg})
        messages.chat_message("assistant").write(msg)

    def open_ai_generate_JSON():
        # Ask ChatGPT to make a JSON File of the information and update JSON
        client = st.session_state.open_ai_client
        # sometimes the json format is not valid, rerun a couple of times
        max_attempts = 2
        attempt = 1
        success = False
        while attempt < max_attempts and not success:
            try:
                tmp_message = st.session_state.messages.copy()
                tmp_message.append({"role": "user", "content": system_prompt_JSON})
                response = client.chat.completions.create(model="gpt-3.5-turbo", messages=tmp_message)
                st.session_state.open_ai_json_string = json.loads(response.choices[0].message.content)

                success = True  # If parsing succeeds, set success to True to exit the loop
            except json.JSONDecodeError:
                attempt += 1  # Increment the attempt counter if JSON parsing fails

        if not success:
            st.error("Failed to process response after 2 attempts.")

    def open_ai_generate_JSON_OnlyDelta():
        # Ask ChatGPT to make a JSON File of the information and update JSON
        client = st.session_state.open_ai_client
        # sometimes the json format is not valid, rerun a couple of times
        max_attempts = 2
        attempt = 1
        success = False
        while attempt < max_attempts and not success:
            try:
                tmp_message = st.session_state.messages.copy()
                tmp_message = tmp_message[-2:]
                json_data=st.session_state.all_content_information.copy()
                json_data.pop('use_cases', None)
                prompt=system_prompt_JSON_Delta+json.dumps(json_data, indent=4)
                tmp_message.append({"role": "user", "content": prompt})
                response = client.chat.completions.create(model="gpt-3.5-turbo", messages=tmp_message)
                st.session_state.open_ai_json_string = json.loads(response.choices[0].message.content)


                success = True  # If parsing succeeds, set success to True to exit the loop
            except json.JSONDecodeError:
                attempt += 1  # Increment the attempt counter if JSON parsing fails

        if not success:
            st.error("Failed to process response after 3 attempts.")


    def map_openAIJSON_to_local_variable_Delta():
        st.session_state.all_content_information = copy.deepcopy(st.session_state.open_ai_json_string)
        use_case_user_details = st.session_state.use_cases_user_details

        value_chain_data = st.session_state.all_content_information.get("value_chain", None)
        if value_chain_data != None and len(value_chain_data) > 0:
            for curr_comp_el in value_chain_data:
                current_use_cases = curr_comp_el.get("use_cases", None)
                curr_comp_name= curr_comp_el.get("name", None)
                if current_use_cases is not None:
                    for curr_use_case_elem in current_use_cases:
                        curr_use_case_name=curr_use_case_elem.get("name")
                        use_case_details_key = curr_comp_name + "_" + curr_use_case_name

                        if use_case_details_key not in use_case_user_details:
                            use_case_user_details[use_case_details_key] = {
                                "comment": "", "prio": "Not Rated"}
                        curr_use_case_elem["component"]=curr_comp_name



    def map_openAIJSON_to_local_variable():
        output_openAI=st.session_state.open_ai_json_string
        use_case_user_details=st.session_state.use_cases_user_details
        data={}
        data["company_name"]=output_openAI["company_name"]
        data["company_description"] = output_openAI["company_description"]

        data["value_chain"]=[]
        data["use_cases"]=[]

        value_chain_data = st.session_state.open_ai_json_string.get("value_chain", None)
        if value_chain_data != None and len(value_chain_data)>0:
            for i, component_name in enumerate(value_chain_data.keys()):
                component_info={}
                component_info["name"]=component_name
                component_info["description"]=value_chain_data[component_name]["description"]
                component_info["use_cases"]=[]

                current_use_cases = value_chain_data.get(component_name).get("use_cases", None)
                if current_use_cases is not None:
                    for use_case_name in current_use_cases.keys():
                        use_case_details_key=component_name + "_" + use_case_name

                        if use_case_details_key not in use_case_user_details:
                            use_case_user_details[use_case_details_key] = {
                                "comment": "", "prio": "Not Rated"}

                        use_case_info={}
                        use_case_info["name"] = use_case_name
                        use_case_info["description"] = current_use_cases.get(use_case_name).get("description", "")
                        use_case_info["component"]=component_name
                        data["use_cases"].append(use_case_info)
                        component_info["use_cases"].append(use_case_info)
                data["value_chain"].append(component_info)

        st.session_state.all_content_information=data




    with chatbot_container:
        st.header("💬 Chatbot")

        messages = st.container(height=500)

        #Initialize chatbot the first thime
        if not st.session_state.initialized_chat:
            response = st.session_state.open_ai_client.chat.completions.create(model="gpt-3.5-turbo",
                                                                               messages=st.session_state.messages)
            msg = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.session_state.initialized_chat=True

        #Add all Chatbot messages in the Chat UI
        for msg in st.session_state.messages:
            if (msg['role'] == "system"):
                continue
            messages.chat_message(msg["role"]).write(msg["content"])

        #Add a Chatbot Prompt and trigger openai client if user prompts something, additionally store retrieved json data
        if prompt := st.chat_input():
            #Get andwer form OpenAI
            open_ai_get_answer()

            #Get Json information form OpenAI an map to the local json
            # with whole chat messages:
            open_ai_generate_JSON()
            map_openAIJSON_to_local_variable()

            #with just the last messages of the chat
            #open_ai_generate_JSON_OnlyDelta()
            #map_openAIJSON_to_local_variable_Delta()

            ##SCRIPT IS NOT re-run after her, so let's do it manually (important to update ui)
            st.rerun()


    # -------COMPANY CONTAINER-------
    col_company_name, col_company_information = company_container.columns(2)
    with col_company_name:
        st.text_input('Company Name', st.session_state.all_content_information["company_name"], disabled=True)

    with col_company_information:
        st.text_area('Company Description', st.session_state.all_content_information["company_description"], disabled=True)

    # -------VALUE CHAIN CONTAINER----------

    if "value_chain" in st.session_state.all_content_information:
        value_chain_data = st.session_state.all_content_information["value_chain"]
        if len(value_chain_data)> 0:
            #create for each component a column
            cols = value_container.columns(len(value_chain_data))

            #iterate over the components
            for i , component in enumerate(value_chain_data):
                col = cols[i]

                #Add container and caption for new component
                container = col.container(border=True, height=300)
                container.caption(component["name"])

                #Fill it with the available use cases
                use_cases = component["use_cases"]
                for use_case in use_cases:
                    use_case_details_key=component["name"] + "_" + use_case["name"]
                    container.button(use_case["name"], on_click=show_use_cases_in_datails_UI,
                                     args=[use_case, use_case_details_key])


        else:
            value_container.write("Value chain not defined yet")

    # -------USECASE CONTAINER----------
    if  "use_cases" in st.session_state.all_content_information:
        use_cases = copy.deepcopy(st.session_state.all_content_information["use_cases"])
        use_cases_details=st.session_state.use_cases_user_details
        if len(use_cases)>0:
            with (usecase_container):
                usecase_list=[]
                for use_case in use_cases:
                    use_case_key=use_case["component"] + "_" + use_case["name"]
                    use_case["comment"]=use_cases_details[use_case_key]["comment"]
                    use_case["prio"]=use_cases_details[use_case_key]["prio"]
                    usecase_list.append(use_case)

                # Configure grid options using GridOptionsBuilder
                df=pd.DataFrame.from_records(usecase_list)
                builder = GridOptionsBuilder.from_dataframe(df)
                builder.configure_pagination(enabled=True)
                builder.configure_selection(selection_mode='single', use_checkbox=False)

                builder.configure_default_column(
                    flex=1,
                    minWidth=100,
                    maxWidth=500,
                    resizable=True,
                )

                grid_options = builder.build()

                # On Selection
                return_value = AgGrid(df, gridOptions=grid_options)
                if return_value['selected_rows']:
                    row=return_value['selected_rows'][0]
                    use_case_details_key=row["component"] +"_"+ row["name"]
                    show_use_cases_in_datails_UI(row, use_case_details_key)#(use_case, use_case_name, use_case_dict)


        else:
            usecase_container.write("No use cases yet")


    #--------GENERATE REPORT -----------

    def get_session_data():
        session={}
        session['content']=st.session_state.all_content_information
        session['chat_messages'] = st.session_state.messages
        session['user_data']=st.session_state.use_cases_user_details
        return session

    def set_session_data(session):
        st.session_state.all_content_information=session['content']
        st.session_state.messages=session['chat_messages']
        st.session_state.use_cases_user_details=session['user_data']





    # -------DETAILS CONTAINER----------

    def save_usecase_details(usecase_key, comment,prio):
        st.session_state.use_cases_user_details[usecase_key]["comment"] = comment
        st.session_state.use_cases_user_details[usecase_key]["prio"] = prio


    if st.session_state.use_case_details_displayed is None:
        details_container.write("Please select a use case below")
    else:
        details_container.text_input('Name', value=st.session_state.use_case_details_displayed["name"], disabled=True)
        details_container.text_area('Description', value=st.session_state.use_case_details_displayed["description"], disabled=True)
        dict_key=st.session_state.use_case_details_displayed["dict_key"]
        comment = details_container.text_area('Comment', value=st.session_state.use_cases_user_details[dict_key]["comment"])

        prio=details_container.selectbox("Prio", ["Not Rated","low","medium","high"],["Not Rated","low","medium","high"].index(st.session_state.use_cases_user_details[dict_key]["prio"]))
        details_container.button("save", on_click=save_usecase_details,
                                 args=[dict_key, comment, prio])


    # custom_css = """
    # <style>
    # button {
    #    padding: 0.25rem 0.5rem !important; /* Smaller padding */
    #    font-size: 0.875rem !important; /* Smaller font size */
    #    margin: 0.5rem 0 !important; /* Adjust margin as needed */
    # }
    # </style>
    # """
    # st.markdown(custom_css, unsafe_allow_html=True)



    # -------SESSION CONTAINER----------
    with session_container:
        st.title("Generate PDF Report")
        if "use_cases" in st.session_state.all_content_information:
            st.download_button(
                label="Save Session as PDF",
                data=report.create_pdf_report(get_session_data()),
                file_name='session.pdf',
                mime='application/pdf'
            )
        else:
            st.write("Please generate first some use casess")

        st.title("Load/Save")
        session_file_name = st.text_input('Enter filename:', value="session.pkl")

        if st.button('Save on Server'):
            if session_file_name:  # Check if the filename is not empty
                with open(session_file_name, 'wb') as file:
                    pickle.dump( get_session_data(), file)
                st.success(f'File "{session_file_name}" saved successfully!')
            else:
                st.success("Please enter a valid filename.")


        if st.button('Load from Server'):
            if session_file_name:  # Check if the filename is not empty
                with open(session_file_name, 'rb') as file:
                    set_session_data(pickle.load(file))
                st.success(f'Session "{session_file_name}" loaded successfully!')
                st.rerun()
            else:
                st.success("Please enter a valid filename.")

        # Use st.download_button to make the prettified text downloadable
        st.download_button(
            label="Download session data",
            data=pickle.dumps(get_session_data()),
            file_name='session.pkl',
            mime='text/plain',
        )

        upload_session_file = st.file_uploader("Upload and load session")
        if upload_session_file is not None:
            set_session_data(pickle.load(upload_session_file))
            st.success(f'Session "{session_file_name}" loaded successfully!')



    # -------DEBUGGER CONTAINER----------
    with debugger_container:
        # st.caption("debugger")

        st.write("all_content_information")
        st.write(st.session_state.all_content_information)

        st.write("use_cases_user_details")
        st.write(st.session_state.use_cases_user_details)

        st.write("GenAI Messages")
        st.write(st.session_state.messages)

        st.write("GenAI JSON")
        st.write(st.session_state.open_ai_json_string)



        st.write("Error Messages")
        st.write(st.session_state.error_messages)
else:
    st.write("Please provide open AI key in the sidebar first")
