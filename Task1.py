import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain.prompts import ChatPromptTemplate
from langchain_community.embeddings.spacy_embeddings import SpacyEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.tools import Tool
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, initialize_agent, Tool as AgentTool
from langchain.agents import AgentType

# Load environment variables
load_dotenv()

# Check if the API key is set
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    st.error("Please set the ANTHROPIC_API_KEY in your environment variables.")
    st.stop()

# Initialize embeddings
embeddings = SpacyEmbeddings(model_name="en_core_web_sm")

# PDF reader function
def pdf_read(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            st.error(f"Error reading {pdf.name}: {e}")
    return text

# Function to split the text into chunks
def get_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return text_splitter.split_text(text)

# Vector store for storing text chunks
def vector_store(text_chunks):
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_db")
    return vector_store

# Define a retriever tool function
def pdf_extractor(query: str):
    # Load the vector store
    new_db = FAISS.load_local("faiss_db", embeddings, allow_dangerous_deserialization=True)
    retriever = new_db.as_retriever()

    # Get relevant documents
    results = retriever.get_relevant_documents(query)
    return results

# Function to handle user input and query
def user_input(user_question):
    try:
        # Define the tool correctly
        pdf_extractor_tool = Tool(
            name="pdf_extractor",
            func=pdf_extractor,
            description="This tool extracts relevant information from the uploaded PDFs"
        )

        # Use the tool in the agent
        tools = [pdf_extractor_tool]

        # Define the LLM
        llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0, api_key=API_KEY, verbose=True)

        # Set up the agent with the tool
        agent = initialize_agent(
            tools,
            llm,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )

        # Get the response from the agent
        response = agent.run(user_question)
        st.write("Reply: ", response)
        
    except Exception as e:
        st.error(f"Error during processing: {e}")

# Main function for the Streamlit app
def main():
    st.set_page_config("Chat PDF")
    st.header("RAG-based Chat with PDF")
    st.sidebar.title("Menu:")

    with st.sidebar:
        pdf_docs = st.file_uploader("Upload PDF Files", type=["pdf"], accept_multiple_files=True)
        if st.button("Submit & Process"):
            if pdf_docs:
                with st.spinner("Processing PDFs..."):
                    raw_text = ""
                    for uploaded_pdf in pdf_docs:
                        raw_text += pdf_read([uploaded_pdf])
                    if raw_text.strip():
                        text_chunks = get_chunks(raw_text)
                        vector_store(text_chunks)
                        st.success("PDFs processed! You can now ask questions.")
                    else:
                        st.error("No text extracted from the uploaded PDFs.")
            else:
                st.warning("Please upload at least one PDF file.")

    user_question = st.text_input("Ask a question about the uploaded PDFs:")
    if user_question:
        user_input(user_question)

if __name__ == "__main__":
    main()
