import os.path
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
  creds = None

  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    return build("drive", "v3", credentials=creds)
  except HttpError as error:
    # TODO Handle errors from drive API.
    print(f"An error occurred: {error}")


def find_storage(service):
    folderID = None

    file_metadata = {
        "name": "SlimSyncStorage",
        "mimeType": "application/vnd.google-apps.folder",
    }

    files = []
    page_token = None

    dirsFound = 0
    while True:
        response = (
        service.files()
        .list(
            q="mimeType='" + file_metadata["mimeType"] + "' and name = '" + file_metadata["name"] + "'",
            spaces="drive",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
        )
        .execute()
        )

        for file in response.get("files", []):
            print(f'Found file: {file.get("name")}, {file.get("id")}')
            dirsFound += 1
            folderID = file.get("id")
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken", None)

        if page_token is None:
          break

    if dirsFound == 0:
        file = service.files().create(body=file_metadata, fields="id").execute()
        print(f'Created Folder ID: "{file.get("id")}".')
        folderID = file.get("id")
    
    return folderID

def upload_file(service, remote_root, local_path):
    file_metadata = {
        'name': os.path.basename(local_path),
        'parents': [remote_root]
    }
    
    media = MediaFileUpload(local_path, resumable=True)
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"Uploaded {local_path} -> Drive ID: {uploaded.get('id')}")
    return uploaded.get('id')

def create_drive_folder(service, remote_root, name):
    folder_metadata = {
      'name': name,
      'parents': [remote_root],
      "mimeType": "application/vnd.google-apps.folder"
    }

    file = service.files().create(body=folder_metadata, fields="id").execute()
    return file.get('id')
   

def upload(service, remote_root, local_root):
   for root, dirs, files in os.walk(local_root):
      for file in files:
        print (os.path.join(root, file))
        #  yield os.path.join(root, file)

# CHECK IF DIR EXISTS, IF NOT CREATE DIR AND ALL SUBSEQUENT FILES
   

   
#    print(local_root)

if __name__ == "__main__":
  service = get_drive_service()
  f_id = find_storage(service)

  local_f = "C:\\Users\\micha\\Downloads\\SSTest"
  upload(service, f_id, local_f)
