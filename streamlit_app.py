import streamlit as st
import asyncio, websockets
import requests
import json
import os

class ChatApplication:
    def __init__(self):        
        print()
        self.user_email = "admin@speciate.com"
        self.stream_resposnse_flag = True

        domain_suffix = ".api.speciate.com"
        env_prefix = os.getenv('ENV', "dev")
        http_api_url = "https://"+env_prefix+domain_suffix ;
        ws_api_url = "ws://"+env_prefix+domain_suffix ;
        
        self.config_connect_url=http_api_url+"/v1/configs/"
        self.chat_connect_url=ws_api_url+"/v1/chat-agents/chat-message"
        print("config_connect_url:" + self.config_connect_url)
        print("chat_connect_url:" + self.chat_connect_url)

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {'role': "user", "content": ""},
                {'role': "assistant", "content": "Understood"},
            ]

    def display_title (self):
        st.title("Chat with Speciate Agent")
        hide_decoration_bar_style = '''
            <style>
                header {visibility: hidden;}
            </style>
        '''
        st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

    def display_config (self):
        response = requests.get(self.config_connect_url)
        if (response.ok):
            config_parent = json.loads(response.content)
            config = config_parent['config']
            container = st.container(border=True)
            container.write("_Current Configuration_")
            container.write("Model: " + ":blue["+config['LLM.MODEL_NAME']+"]")
            container.write("Log Count: :blue[" + str(config['LLM.CONTEXT_LOG_COUNT']) + "]")
            col1, col2 = container.columns([0.2, 0.8], gap="small", vertical_alignment="center")
            col1.markdown("Enter Your Email: ")
            self.user_email = col2.text_input("Enter Your Email: ", value=self.user_email, key="email", max_chars=50, label_visibility="collapsed")

    def display_chat_conversation (self):
        # Display user and assistant messages skipping the first two
        for message in st.session_state.messages[2:]:
            # ignore tool use blocks
            if isinstance(message["content"], str):
                st.chat_message(message["role"]).markdown(message["content"])

    def get_connection_url (self):
        return self.chat_connect_url+"?user_email="+self.user_email+"&stream_response="+str(self.stream_resposnse_flag)

    async def handle_chat_response(self, chat_request, chat_response_placeholder):
        try:
            async with websockets.connect(self.get_connection_url()) as websocket:
                await websocket.send(chat_request)

                full_chat_response = ""
                while True:
                    chat_response = await websocket.recv()
                    if chat_response == "END_OF_STREAM_RESPONSE":
                        break
                    full_chat_response += chat_response
                    chat_response_placeholder.markdown(full_chat_response)
                    if self.stream_resposnse_flag == False:
                        break
                return full_chat_response    
        except Exception as e:
            print(str(e))

    async def handle_chat_conversation (self):
        if chat_request := st.chat_input("How can I help you today?"):
            st.chat_message("user").markdown("(" + self.user_email + ") " + chat_request)
            st.session_state.messages.append({"role": "user", "content": "(" + self.user_email + ") " + chat_request})

            with st.chat_message("assistant"):
                with st.spinner("Thinking aloud..."):
                    chat_response_placeholder = st.empty()
                    full_chat_response = await self.handle_chat_response(chat_request, chat_response_placeholder)
                    st.session_state.messages.append({"role": "assistant", "content": full_chat_response})
    
chatApp = ChatApplication()

def main():
    chatApp.display_title()

    chatApp.display_config()

    chatApp.display_chat_conversation()

    asyncio.run(chatApp.handle_chat_conversation())

if __name__ == "__main__":
   main()
