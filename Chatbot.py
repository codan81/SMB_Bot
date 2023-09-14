

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
from datetime import datetime, timedelta # import delta modules

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

# Function to save chat history to txt file
def save_chat_history(chat_history, customer_name):
    chat_history_folder = "chat_history"
    os.makedirs(chat_history_folder, exist_ok=True)
    chat_history_file = os.path.join(chat_history_folder, f"{customer_name}_chat_history.txt")

    # Open the file in append mode and write the conversation
    with open(chat_history_file, mode='a') as file:
        user_input, bot_response = chat_history[-1] # Get the last interaction
        file.write(f"{customer_name}: {user_input}\n")
        file.write(f"SMB Bot: {bot_response}\n")

    
    # Clean up old chat history files (older than 30 days)
    cleanup_old_chat_history(chat_history_folder)

def cleanup_old_chat_history(folder):
    max_age_days = 30
    current_time = datetime.now()
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
        if current_time - file_creation_time > timedelta(days=max_age_days):
            os.remove(file_path)


# Check if the file customer_info.csv exists or create it if it doesn't
if not os.path.exists("customer_info.csv"):
    with open("customer_info.csv", mode="w", newline='') as info_file:
        # Create a CSV writer object
        info_writer = csv.writer(info_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # Write a header row (if needed)
        info_writer.writerow(["Customer Name", "User Email"])
        

# Read the customer name from the CSV file if available
# Now you can safely read the customer name from the file
customer_name = ""
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

    # # Modify the user input to guide the conversation towards marketing
    # # You can add a query that encourages marketing-related responses
    # user_input = "Merketing"


    # Generate a response from the chatbot model based on the user's query
    result = chain({"question": user_input, "chat_history": chat_history})

    # Limit the response length to a certain number of tokens
    response_tokens = result['answer'].split()
    if len(response_tokens) > max_response_tokens:
        result['answer'] = ' '.join(response_tokens[:max_response_tokens]) + "..."  # Truncate the response

    # Manually truncate and summarize the response
    summary = "SMB Bot: Our marketing services include customized solutions, expertise, personalized attention, innovative solutions, and measurable results."


    # Check if the response from the bot indicates it doesn't have certain information keywords
    keywords_to_trigger_apology = ["I'm sorry", "I apologize", "I don't have", "I don't know" ]

    # Check if the response from the bot contains specific keywords
    keywords_to_trigger_pricing = ['price', 'cost', 'pricing']
    
    # Check if the response from the bot contains specific keywords
    keywords_for_services= ['benefits', 'features', 'services', "seo"]

    # Check if the response from the bot contains specific keywords
    keywords_for_social_media= ['social media', 'instagram', 'facebook', 'youtube', "contact"]

    response = None # Initialize response

    if any(keyword in result['answer'].lower() for keyword in keywords_to_trigger_apology):
        response = Markup(f"SMB Bot: I apologize, but I don't have access to specific information at the moment. " \
                   f"You can find more information or get in touch with us by visiting our " \
                   f"<a href='https://smbglobalmarketing.com/get-in-touch/' target='_blank'>Contact Us</a> page on our website. " \
                   f"Is there anything else I can assist you with?<br><br>")

    if any(keyword in user_input.lower() for keyword in keywords_to_trigger_pricing):
        response = Markup(f"SMB Bot: Our pricing structure is flexible and based on the specific needs and scope of each project." \
                   f"We offer both one-time and ongoing marketing services, and our rates vary depending on factors such as the complexity of the project, the number of channels and tactics involved, and the expected outcomes."\
                   f"We provide transparent pricing quotes and detailed proposals before starting any project, so our clients know exactly what to expect and can make informed decisions. "\
                   f"You can find more information or get in touch with us by visiting our " \
                   f"<a href='https://smbglobalmarketing.com/get-in-touch/' target='_blank'>Contact Us</a> page on our website. " \
                   f"Is there anything else I can assist you with?<br><br>")                   

    elif any(keyword in user_input.lower() for keyword in keywords_for_services):
        response = Markup(f"SMB Bot: {result['answer']} \n\n" \
               f"If you like to learn more about our offerings, you can visit " \
               f"<a href='https://smbglobalmarketing.com/services/' target='_blank'>services</a> page on our website.")

    elif any(keyword in user_input.lower() for keyword in keywords_for_social_media):
        response = Markup(f"SMB Bot: {result['answer']} \n\n" \
                f"SMB Bot: You can connect with us by Email at: <a href='mailto:hello@smbglobalmarketing.com'>hello@smbglobalmarketing.com</a> or thru our various social media platforms. "
                f"Find us on <a href='https://www.facebook.com/smbglobalmarketing' target='_blank'>Facebook</a>, "
                f"<a href='https://www.instagram.com/smbglobalmarketing/' target='_blank'>Instagram</a>, and "
                f"<a href='https://www.youtube.com/channel/UCpsCOYtpNzO8KnbpLnESBTA' target='_blank'>Youtube</a> for updates and news.")

    elif 'email' in result['answer'].lower():
        # Handle email-related query
        response = Markup(f"SMB Bot: You can reach out to us via email at: <a href='mailto:hello@smbglobalmarketing.com'>hello@smbglobalmarketing.com</a>")
                

    if response is None:
        response = Markup(f"SMB Bot: {result['answer']}")  # Remove the extra line breaks

    # Use the | safe filter to mark the response as safe HTML content
    response = Markup(response)

    # Print the response variable for debugging purposes
    print("Response Variable:", response)

    # Save the chat interaction to the chat history list
    # chat_history.append((user_input, result['answer']))
    chat_history.append((user_input, response))  # Save the response triggered by keywords
    
    # Save the chat history to a txt file
    save_chat_history(chat_history, customer_name)
    
    # Send the bot's response as a JSON object to the front end
    return jsonify({'response': response})


if __name__ == '__main__':
    app.run(debug=True, port=8000)  # Change the port to 8000 or any available port
