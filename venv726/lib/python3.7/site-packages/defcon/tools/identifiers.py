import random

characters = list("0123456789")
characters += list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
characters += list("abcdefghijklmnopqrstuvwxyz")
identifierLength = 10
identifierRange = range(identifierLength)

def makeRandomIdentifier(existing, recursionDepth=0):
    if recursionDepth >= 50:
        raise NotImplementedError("Failed 50 times in a row to create a unique id. Sorry.")
    identifier = []
    for i in identifierRange:
        c = random.choice(characters)
        identifier.append(c)
    identifier = "".join(identifier)
    if identifier in existing:
        return makeRandomIdentifier(existing, recursionDepth+1)
    else:
        return identifier
