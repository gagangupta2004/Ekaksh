import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt
from langchain_groq import ChatGroq
from langchain.chains import LLMMathChain, LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.agents.agent_types import AgentType
from langchain.agents import Tool, initialize_agent
from langchain.callbacks import StreamlitCallbackHandler

# Database setup
engine = create_engine('sqlite:///users.db')
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

# Create table
Base.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Helper functions for password hashing and verification
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

# Custom CSS for styling, including hover effect
def add_custom_css():
    st.markdown("""
        <style>
            /* Centering elements */
            .stTextInput > div {
                margin-left: auto;
                margin-right: auto;
            }

            /* Styling buttons with hover effect and transition */
            .stButton > button {
                margin-left: auto;
                margin-right: auto;
                width: 100%;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                border: none;
                font-size: 18px;
                cursor: pointer;
                transition: all 0.3s ease-in-out;
            }
            .stButton > button:hover {
                transform: scale(1.1);  /* Enlarges the button on hover */
                background-color: #45a049;
            }

            /* Container for main assistant interface */
            .assistant-container {
                background-color: #f4f4f4;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                margin-top: 20px;
            }
            /* Custom title */
            .main-title {
                color: #4CAF50;
                text-align: center;
                font-size: 40px;
                font-weight: bold;
                margin-bottom: 20px;
            }
            /* Secondary title */
            .secondary-title {
                color: #333;
                text-align: center;
                font-size: 24px;
                font-weight: normal;
            }
        </style>
    """, unsafe_allow_html=True)

# Set up the Langchain-powered Assistant
# Hardcoded Groq API key (replace with your actual API key)
groq_api_key = "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"

# Initialize the LLM (Groq model)
llm = ChatGroq(model="Gemma2-9b-It", groq_api_key=groq_api_key)

# Tool 1: Wikipedia for information retrieval
wikipedia_wrapper = WikipediaAPIWrapper()
wikipedia_tool = Tool(
    name="Wikipedia",
    func=wikipedia_wrapper.run,
    description="A tool for searching the Internet to find various information on the topics mentioned"
)

# Tool 2: Math solver tool (LLMMathChain)
math_chain = LLMMathChain.from_llm(llm=llm)
calculator = Tool(
    name="Calculator",
    func=math_chain.run,
    description="A tool for answering math-related questions. Only input mathematical expressions are needed."
)

# Tool 3: Code generation prompt template
code_prompt = """
You are an expert code generator. Given the task below, generate optimized and efficient code with clear comments. 
Task: {task}
Generated Code:
"""
code_prompt_template = PromptTemplate(input_variables=["task"], template=code_prompt)
code_chain = LLMChain(llm=llm, prompt=code_prompt_template)
code_generator = Tool(
    name="Code Generator",
    func=code_chain.run,
    description="A tool for generating code based on user requirements."
)

# Tool 4: Math reasoning prompt template
math_reasoning_prompt = """
You are a math assistant tasked with solving users' mathematical questions. Logically arrive at the solution and provide a detailed explanation point-wise for the question below.
Question: {question}
Answer:
"""
math_reasoning_prompt_template = PromptTemplate(input_variables=["question"], template=math_reasoning_prompt)
math_reasoning_chain = LLMChain(llm=llm, prompt=math_reasoning_prompt_template)
reasoning_tool = Tool(
    name="Math Reasoning",
    func=math_reasoning_chain.run,
    description="A tool for answering complex math problems with logical reasoning."
)

# Initialize the agent with both code generation and math-solving tools
assistant_agent = initialize_agent(
    tools=[wikipedia_tool, calculator, reasoning_tool, code_generator],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
    handle_parsing_errors=True
)

# Streamlit app setup
st.set_page_config(page_title="Ekaksh - Math & Code Assistant", page_icon="🧮")

# Register form
def register_user():
    add_custom_css()
    st.markdown('<div class="main-title">Register</div>', unsafe_allow_html=True)
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
    
    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match!")
        else:
            # Check if user already exists
            if session.query(User).filter_by(username=username).first():
                st.error("Username already exists! Please choose another one.")
            else:
                hashed_password = hash_password(password)
                new_user = User(username=username, password=hashed_password)
                session.add(new_user)
                session.commit()
                st.success("Registration successful! Please log in.")

# Login form
def login_user():
    add_custom_css()
    st.markdown('<div class="main-title">Login</div>', unsafe_allow_html=True)
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    
    if st.button("Login"):
        user = session.query(User).filter_by(username=username).first()
        if user and check_password(user.password, password):
            st.success("Login successful!")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Invalid username or password")

# Main assistant interface
def assistant_interface():
    add_custom_css()
    st.markdown(f'<div class="main-title">Welcome, {st.session_state["username"]}!</div>', unsafe_allow_html=True)
    st.markdown('<div class="secondary-title">How can I assist you today?</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="assistant-container">', unsafe_allow_html=True)
        query = st.text_area("Enter your math problem or code generation task:", height=200, placeholder="Ask me anything...")
        
        if st.button("Get Answer"):
            if query:
                if "code" in query.lower() or "function" in query.lower() or "script" in query.lower():
                    response = assistant_agent.run(f"Generate code for the following task: {query}")
                else:
                    response = assistant_agent.run(f"Solve this math problem: {query}")
                st.write("### Response:")
                st.success(response)
            else:
                st.warning("Please enter a valid query")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Go to Veriface"):
        st.write("[Go to Veriface](https://veriface.streamlit.app)")

# App logic
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    choice = st.sidebar.radio("Select an option", ["Login", "Register"])
    if choice == "Login":
        login_user()
    elif choice == "Register":
        register_user()
else:
    assistant_interface()
