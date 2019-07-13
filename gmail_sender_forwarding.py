import os
import base64
import email
from scheduler import scheduler
from gmail_service import service, user_id
from gmail_message import ListMessagesMatchingQuery, GetMessage

timestamp_file = 'timestamp.txt'
subscribers_file = 'subscribers.txt'
key_file = 'key.txt'
subscription_message = 'This message has been forwarded to you because you subscribed to my service'


def init_sender(sender):
    if not os.path.isdir(sender):
        os.mkdir(sender)
        last_time = get_timestamp(sender)
        with open(os.path.join(sender, timestamp_file), 'w+') as f:
            f.write(last_time)

        with open(os.path.join(sender, key_file), 'w+') as f:
            f.write(sender + '654869735967345896794358' + '\n')
            f.write(sender + 'jfiwefjewifjweifgerggrergj' + '\n')

        open(os.path.join(sender, subscribers_file), 'w+').close()


def update_timestamp(sender):
    timestamp = get_ref_timestamp(sender)
    print("Old Timestamp", timestamp)
    new_timestamp = get_timestamp(sender, timestamp=timestamp)
    print("New Timestamp", new_timestamp)
    set_ref_timestamp(sender, new_timestamp)


def get_ref_timestamp(sender):
    with open(os.path.join(sender, timestamp_file)) as f:
        timestamp = int(f.readline())
    return timestamp


def set_ref_timestamp(sender, timestamp):
    with open(os.path.join(sender, timestamp_file), 'w+') as f:
        f.write(str(timestamp))


def get_timestamp(sender, timestamp=None):
    msgs = list_messages(sender, timestamp)
    if len(msgs) == 0:
        return timestamp if timestamp is not None else 0
    # print(len(msgs), msgs[-1])
    # print(len(msgs), msgs[0])
    # print(GetMessage(service=service, user_id=user_id,
    #                  msg_ids=[msgs[0]['id']]))
    # print(GetMessage(service=service, user_id=user_id,
    #                  msg_ids=[msgs[0]['id']]
    #                  )[0]['internalDate'])
    # print(GetMessage(service=service, user_id=user_id,
    #                  msg_ids=[msgs[-1]['id']]
    #                  )[0]['internalDate'])
    return GetMessage(service=service, user_id=user_id,
                      msg_ids=[msgs[0]['id']]
                      )[0]['internalDate']


def list_messages(sender, timestamp):
    query = "from:{}".format(sender)
    if timestamp is not None:
        query += " after:{}".format(str(timestamp))
    return ListMessagesMatchingQuery(service=service,
                                     user_id=user_id,
                                     q=query)


def get_stamped_mime_messages(sender):
    msgs = list_messages(sender, get_ref_timestamp(sender))
    if len(msgs) == 0:
        return []

    msgs_content = GetMessage(service=service, user_id=user_id,
                              msg_ids=[m['id'] for m in msgs],
                              format="raw"
                              )

    mime_msgs = []
    for m in msgs_content[:3]:
        msg_str = base64.urlsafe_b64decode(m['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)

        mime_msgs.append(mime_msg)
    return mime_msgs


def get_key(sender):
    with open(os.path.join(sender, key_file)) as f:
        sub_key = str(f.readline())
        unsub_key = str(f.readline())
    return sub_key, unsub_key


def get_subscribers(sender):
    with open(os.path.join(sender, subscribers_file)) as f:
        subscribers = set(u for u in f.readlines())
    return subscribers


def set_subscribers(sender, subscribers):
    with open(os.path.join(sender, subscribers_file)) as f:
        for s in subscribers:
            f.write(s)


def update_subscribers(sender):
    timestamp = get_ref_timestamp(sender)
    sub_key, unsub_key = get_key(sender)
    subscribers = get_subscribers(sender)

    query = '{} OR {}'.format(sub_key, unsub_key)
    if timestamp is not None:
        query += " after:{}".format(str(timestamp))
    msgs = ListMessagesMatchingQuery(service=service,
                                     user_id=user_id,
                                     q=query)
    if len(msgs) == 0:
        return

    msgs_content = GetMessage(service=service, user_id=user_id,
                              msg_ids=[m['id'] for m in msgs],
                              format="metadata",
                              metadataHeaders=['From']
                              )

    for m in msgs_content:
        snip = m['snippet']
        one_sender = m['payload']['headers'][0]['value']
        if sub_key in snip:
            subscribers.add(one_sender)
        if unsub_key in snip:
            subscribers.remove(one_sender)
    set_subscribers(sender, subscribers)


def listen_and_deliver(sender):
    msgs = get_stamped_mime_messages(sender)
    if not msgs:
        return
    subscribers = get_subscribers(sender)
    if not subscribers:
        return
    for m in msgs:
        m['To'] = ', '.join(subscribers)
        message = {'raw': base64.urlsafe_b64encode(m.as_bytes()).decode()}
        message_ = service.users().messages().send(userId=user_id, body=message).execute()
        print(message_)
    print("Done")


def run_process(sender):
    init_sender(sender)
    update_timestamp(sender)

    def update():
        update_subscribers(sender)
        listen_and_deliver(sender)
        update_timestamp(sender)

    scheduler.add_job(update, 'interval', hours=1)
    scheduler.start()
