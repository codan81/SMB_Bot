

from flask import Flask, render_template, request, jsonify, redirect
from markupsafe import Markup

import os
import csv
import sys
import openai
from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
from langchain.llms import OpenAI
from langchain.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

PERSIST = False

app = Flask(__name__)

# Initialize the chatbot
chat_history = []
customer_name = ""  # Initialize customer_name as an empty string

# Use this variable to track whether the name and email have been collected
info_collected = False

# Read the customer name from the CSV file if available
if os.path.exists("customer_info.csv"):
    with open("customer_info.csv", mode="r") as info_file:
        info_reader = csv.reader(info_file)
        for row in info_reader:
            if len(row) >= 1:
                customer_name = row[0]
                break
# print("Customer Name:", customer_name)  # Add this line for debugging

# Initialize the chatbot chain
query = None
if PERSIST and os.path.exists("persist"):
    print("Reusing index...\n")
    vectorstore = Chroma(persist_directory="persist", embedding_function=OpenAIEmbeddings())
    index = VectorStoreIndexWrapper(vectorstore=vectorstore)
else:
    loader = DirectoryLoader("data/")
    if PERSIST:
        index = VectorstoreIndexCreator(vectorstore_kwargs={"persist_directory": "persist"}).from_loaders([loader])
    else:
        index = VectorstoreIndexCreator().from_loaders([loader])

chain = ConversationalRetrievalChain.from_llm(
    llm=ChatOpenAI(model="gpt-3.5-turbo"),
    retriever=index.vectorstore.as_retriever(search_kwargs={"k": 1}),
)

@app.route('/')
def chat_interface():
    global info_collected

    # Check if the name and email have been collected
    if not info_collected:
        return render_template('info_form.html')  # Display the info collection form
    else:
        return render_template('chat_interface.html', customer_name=customer_name)

@app.route('/collect_info', methods=['POST'])
def collect_info():
    global customer_name, info_collected

    # Collect and save the name and email from the web form
    customer_name = request.form['customer_name']
    user_email = request.form['user_email']

    # Save the name and email to a CSV file
    with open('customer_info.csv', mode='a', newline='') as info_file:
        info_writer = csv.writer(info_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        info_writer.writerow([customer_name, user_email])

    # Mark info as collected
    info_collected = True

    return redirect('/')  # Redirect back to the chat interface

@app.route('/chat', methods=['POST'])
def chat():
    global info_collected, customer_name

    if not info_collected:
        return redirect('/')  # Redirect to collect info if it hasn't been collected yet

    user_input = request.form['user_input']

    if user_input.lower() in ['quit', 'q', 'exit']:
        sys.exit()

    # Set a maximum token limit for the response
    max_response_tokens = 50  # Adjust this value as needed

    # Generate a response from the chatbot model based on the user's query
    result = chain({"question": user_input, "chat_history": chat_history})

    # Check if the response from the bot indicates it doesn't have certain information or mentions price-related keywords
    keywords_to_trigger_apollogy = ['price', 'cost', 'pricing', 'quote', "I'm sorry", "I apologize", "I don't have" ]
    
    # Check if the response from the bot contains specific keywords
    keywords_for_services= ['benefits', 'features', 'services']

    # Check if the response from the bot contains specific keywords
    keywords_for_social_media= ['social media', 'instagram', 'facebook', 'youtube']


    if any(keyword in result['answer'].lower() for keyword in keywords_to_trigger_apollogy):
        response = Markup(f"SMB Bot: I apologize, but I don't have access to specific information at the moment. " \
                   f"You can find more information or get in touch with us by visiting our " \
                   f"<a href='https://smbglobalmarketing.com/get-in-touch/' target='_blank'>Contact Us</a> page on our website. " \
                   f"Is there anything else I can assist you with?<br><br>")

    elif any(keyword in result['answer'].lower() for keyword in keywords_for_services):
        response = Markup(f"SMB Bot: {result['answer']} \n\n" \
               f"If you like to learn more about our offerings, you can visit " \
               f"<a href='https://smbglobalmarketing.com/services/' target='_blank'>services</a> page on our website.")

    elif any(keyword in result['answer'].lower() for keyword in keywords_for_social_media):
        response = Markup(f"SMB Bot: {result['answer']} \n\n" \
                f"SMB Bot: You can connect with us by Email at: <a href='mailto:hello@smbglobalmarketing.com'>hello@smbglobalmarketing.com</a> or thru our various social media platforms. "
                f"Find us on <a href='https://www.facebook.com/smbglobalmarketing' target='_blank'>Facebook</a>, "
                f"<a href='https://www.instagram.com/smbglobalmarketing/' target='_blank'>Instagram</a>, and "
                f"<a href='https://www.youtube.com/channel/UCpsCOYtpNzO8KnbpLnESBTA' target='_blank'>Youtube</a> for updates and news.")

    elif 'email' in result['answer'].lower():
        # Handle email-related query
        response = Markup(f"SMB Bot: You can reach out to us via email at: <a href='mailto:hello@smbglobalmarketing.com'>hello@smbglobalmarketing.com</a>.")
                

    else:
        response = Markup(f"SMB Bot: {result['answer']}")  # Remove the extra line breaks

    # Use the | safe filter to mark the response as safe HTML content
    response = Markup(response)

    # Print the response variable for debugging purposes
    # print("Response Variable:", response)

    chat_history.append((user_input, result['answer']))
    
    # Send the bot's response as a JSON object to the front end
    return jsonify({'response': response})


if __name__ == '__main__':
    app.run(debug=True, port=8000)  # Change the port to 8000 or any available port
