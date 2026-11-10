import sys

message = sys.stdin.read()

message = "\n".join(
    line for line in message.splitlines()
    if "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" not in line
)

sys.stdout.write(message.rstrip() + "\n")
