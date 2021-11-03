def à_chameau(text):
    # https://stackoverflow.com/questions/60978672/python-string-to-camelcase
    s = text.replace("-", " ").replace("_", " ")
    s = s.split()
    if len(text) == 0:
        return text
    return s[0] + ''.join(i.capitalize() for i in s[1:])
