from __future__ import print_function
import os
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import base64
from email.message import EmailMessage

SCOPE_READ = ['https://www.googleapis.com/auth/gmail.readonly']
SCOPE_WRITE = ['https://www.googleapis.com/auth/gmail.send']
openai.api_key = os.getenv("OPENAI_API_KEY")

# This function reads and returns the content of each unread email in the user's inbox in a list
def getUnreadMails():

	content_list = []
	creds = None
	# The file token.json stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token_read.json'):
		creds = Credentials.from_authorized_user_file('token_read.json', SCOPE_READ)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPE_READ)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('token_read.json', 'w') as token:
			token.write(creds.to_json())

	service = build('gmail', 'v1', credentials=creds)
	# Read unread messages
	results = service.users().messages().list(userId='me', q="is:unread").execute()
	messages = results.get('messages', [])

	if not messages:
		print("You have no new messages.")
	else:
		for message in messages:
			msg = service.users().messages().get(userId='me', id=message['id']).execute()
			emailData = msg["payload"]["headers"]
			for values in emailData:
				name = values["name"]
				if name == "From":
					# extract content and append to a list
					content_list.append(msg["snippet"])

	return (content_list)

# This function generates a TLDR of each unread email by sending prompts to the OpenAI DaVinci Model
def generateSummary(content):
	response_list = []

	for i in content:
		response = openai.Completion.create(
  		model="text-davinci-003",
  		prompt = i + "\n\nTl;dr",
  		temperature=0.5,
  		max_tokens=100,
  		top_p=1.0,
  		frequency_penalty=0.8,
  		presence_penalty=0.0 )

		response_list.append(response["choices"][0]["text"])

	return (response_list)

# This function sends a summary of all unread emails to the user's inbox
def sendTLDRMail(response_list):
	creds = None

	if os.path.exists('token_send.json'):
		creds = Credentials.from_authorized_user_file('token_send.json', SCOPE_WRITE)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPE_WRITE)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('token_send.json', 'w') as token:
			token.write(creds.to_json())

	service = build('gmail', 'v1', credentials=creds)

	message = EmailMessage()

	# HTML formatting for email
	content = "<ol>\n"
	for item in response_list:
		content += f"<li>{item}</li>\n"
	content += "</ol>"


	#message.set_type("text/html")
	message.set_content(content, subtype='html')

	message['To'] = 'anishka18v@gmail.com'
	message['From'] = 'anishka18v@gmail.com'
	message['Subject'] = 'Unread Email To-Do List'

	encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

	message = {
		'raw': encoded_message
	}

	# execute email send
	service.users().messages().send(userId="me", body=message).execute()



if __name__ == '__main__':
	content = getUnreadMails()
	response = generateSummary(content)
	sendTLDRMail(response)
