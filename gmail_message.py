"""Get a list of Messages from the user's mailbox.
"""

from apiclient import errors
from itertools import islice


def ListMessagesMatchingQuery(service, user_id, **kwargs):
    """List all Messages of the user's mailbox matching the query.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      query: String used to filter messages returned.
      Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

    Returns:
      List of Messages that match the criteria of the query. Note that the
      returned list contains Message IDs, you must use get with the
      appropriate ID to get the details of a Message.
    """
    try:
        response = service.users().messages().list(userId=user_id, **kwargs).execute()
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id,
                                                       pageToken=page_token,
                                                       **kwargs).execute()
            messages.extend(response['messages'])

        return messages
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def ListMessagesMatchingSender(service, user_id, sender, **kwargs):
    return ListMessagesMatchingQuery(service, user_id,
                                     q='from:{}'.format(sender),
                                     **kwargs)


def GetMessage(service, user_id, msg_ids, **kwargs):
    """Get a Message with given ID.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_ids: Container of : The ID of the Message required.

    Returns:
      A Message.
    """
    msgs = []

    def fetch(rid, response, exception):
        if exception is not None:
            print("Exception\t", exception)
        else:
            msgs.append(response)

    # Make a batch request
    msgs_it = iter(msg_ids)
    n = 100
    msg_chunk = islice(msgs_it, n)
    while True:
        batch = service.new_batch_http_request()
        empty = True
        for message_id in msg_chunk:
            t = service.users().messages().get(userId=user_id, id=message_id,
                                               **kwargs)
            batch.add(t, callback=fetch)
            empty = False
        if empty:
            break
        batch.execute()
        # print(msgs[-1]['internalDate'])
        # print(msgs[-1]['payload']['headers'][0]['value'])
        msg_chunk = islice(msgs_it, n)

    return msgs


def GetSender(service, user_id, msg_ids, **kwargs):
    """Get a Sender of Message with given ID.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_ids: Container of : The ID of the Message required.

    Returns:
      A Message.
    """
    return GetMessage(service=service,
                      user_id=user_id,
                      msg_ids=msg_ids,
                      format="metadata",
                      metadataHeaders=['From'],
                      **kwargs)
