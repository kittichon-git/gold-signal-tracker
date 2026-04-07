import base64
data = open("gold_tracker_session.session", "rb").read()
print(base64.b64encode(data).decode())
