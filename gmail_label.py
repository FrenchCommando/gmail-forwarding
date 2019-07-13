from gmail_service import service, user_id


# Call the Gmail API
results = service.users().labels().list(userId=user_id).execute()
labels = results.get('labels', [])

if not labels:
    print('No labels found.')
else:
    print('Labels:')
    for label in labels:
        print(label['name'])
