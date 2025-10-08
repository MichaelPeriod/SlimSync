import os.path
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]
STORAGE_NAME = "SlimSyncStorage"
STORAGE_ID = ""
LOCAL_STORE = "C:\\Users\\micha\\Downloads\\SSTest"


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
  return find_folder(service, STORAGE_NAME, create_inf=True)

def find_folder(service, name, parent="", create_inf=False):
    folderID = None

    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    files = []
    page_token = None

    dirsFound = 0

    query = "mimeType='" + file_metadata["mimeType"] + "' and name = '" + file_metadata["name"] + "'"
    # if len(parent) > 0:
    #   query += " and '"+ str(STORAGE_ID) + "' is parent"
    # print(query)
    
    while True:
        response = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
        )
        .execute()
        )

        for file in response.get("files", []):
            print(f'Found folder: {file.get("name")}, {file.get("id")}')
            dirsFound += 1
            folderID = file.get("id")
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken", None)

        if page_token is None:
          break

    if dirsFound == 0 and create_inf:
        file = service.files().create(body=file_metadata, fields="id").execute()
        print(f'Created Folder ID: "{file.get("id")}".')
        folderID = file.get("id")
    
    return folderID

def upload_file(service, parent_name, local_path):
    
    remote_root = find_folder(service, parent_name, STORAGE_NAME)

    file_metadata = {
        'name': os.path.basename(local_path),
        'parents': [remote_root]
    }
    
    print(local_path)
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

def recursive_local_file_scan(curr_dir, dir_stack, to_return):
  with os.scandir(curr_dir) as d:
    for e in d:
      if e.is_dir():
        dir_stack.append(e.name)
        recursive_local_file_scan(curr_dir + os.path.sep + e.name, dir_stack, to_return)
      elif e.is_file():
        file_name = "".join(os.path.sep.join(dir_stack) + os.path.sep + e.name)
        if file_name[0] != "\\":
           file_name = "\\" + file_name
        to_return.add(file_name)
  
  if len(dir_stack) <= 2:
     return
  dir_stack.pop()

def recursive_remote_file_scan(service, curr_parent, dir_stack, to_return):
  res = (
    service.files()
    .list(q="'"+ curr_parent + "' in parents", spaces="drive")
  ).execute()

  for r in res.get("files"):
    if r.get('mimeType') == "application/vnd.google-apps.folder":
      dir_stack.append(r.get("name"))
      recursive_remote_file_scan(service, r.get("id"), dir_stack, to_return)
    else:
      file_name = "".join(os.path.sep.join(dir_stack) + os.path.sep + r.get("name"))
      if file_name[0] != "\\":
        file_name = "\\" + file_name
      to_return.add(file_name)
  
  if len(dir_stack) <= 1:
     return
  dir_stack.pop()

def compare(service, remote_root, local_root):
  #Will compare hashes in the future for version detection

  local_files = set()
  remote_files = set()

  recursive_local_file_scan(local_root, [os.path.basename(local_root)], local_files)
  recursive_remote_file_scan(service, remote_root, [], remote_files)

  diff = [set(), set()]
  for d in (local_files - remote_files):
    diff[0].add(d)
  for d in (remote_files - local_files):
    diff[1].add(d)
  return diff

if __name__ == "__main__":
  service = get_drive_service()
  STORAGE_ID = find_storage(service)

  difference = compare(service, STORAGE_ID, LOCAL_STORE)

  for d in difference[0]:
    print(d.split("\\"))
    file_name = d.split("\\")[-2]
    complete_file_location = LOCAL_STORE+"\\".join(d.split("\\")[::len(d.split("\\"))-1])
    upload_file(service, file_name, complete_file_location)

  print(difference[0])

  #Preform upload and download based on comparison
