# coding: utf-8
#
# notes:
# user/pass are hardcoded!
# my id = 30 is hardcoded!
# me is always set to H323
# todo: login is only for external account! login via shibboleth if in sso_domain ...

my_email = 'XXX@YYY.ZZZ'
my_password = '********'

def start_session():
    """
    Starts a session with e:presence
    user/pass and filters are hardcoded
    return a session and the token
    """

    import requests
    from bs4 import BeautifulSoup
    import json

    LOGIN_URL = "https://new.epresence.grnet.gr/auth/login"

    with requests.Session() as s:

        # Read the source
        r = s.get(LOGIN_URL)
        soup = BeautifulSoup(r.text, 'html5lib')
        # Find the token
        token = soup.find("input", {"name":"_token"} )["value"]

        authinfo = {
            'email': my_email,
            'password': my_password,
            '_token': token
        }

        # Login:
        rl = s.post(LOGIN_URL, data=authinfo)

        return s, token


def fetch_my_id():
    s, _ = start_session()
    e, _ = my_id = check_emails([my_email], s)
    my_id = e[my_email]
    return my_id


def read_emails():
    """
    read multiple lines, keep only emails
    terminate with .
    returns a list of emails
    """

    import re

    lines = []

    print("Give the emails: (end with . on a single line)")
    while True:
        line = input()
        line = line.strip()
        if ( line == '.' ):
            break
        else:
            fields = line.split(',')
            for field in fields:
                if( re.findall(".*@.*", field) ):
                    lines.append(field.strip())
    return lines


def get_sso_domains():

    """
    return a list of shibbolethized domains (stripped to 2nd level domains)
    """

    import requests
    import re
    import os
    from datetime import datetime

    URL = "https://wayf.grnet.gr/"
    OL_FILE = 'internal_domains'

    with requests.Session() as s:

        # Read the source
        try:
            r = s.get(URL)
            r.raise_for_status()
            domains = [ ".".join([d for d in r.split('.')[-2:]]) for r in re.findall('.*option value=.*//([^\/]+)/.*', r.text) ]
            # save an offline backup
            f = open(OL_FILE, "w")
            for domain in domains:
                f.write(domain+'\n')
            f.close()
        except Exception as err:
            print(err)
            print('Falling back to the backup file from ' + str(datetime.fromtimestamp(os.stat(OL_FILE).st_ctime)))
            f = open(OL_FILE)
            domains = f.read().splitlines()
            f.close()

    return domains

def fetch_conf_list():

    """
    Fetch all conferences
    return them in json format
    for use with ical exporter
    """

    from bs4 import BeautifulSoup
    import json

    CONFS_URL = "https://new.epresence.grnet.gr/conferences/all?&limit=1000"

    s, _ = start_session()

    # Now fetch the data
    rc = s.get(CONFS_URL)

    soup = BeautifulSoup(rc.text, 'html5lib')

    data = []
    table = soup.find('table', attrs={'id':'conferenceTable'})
    table_body = table.find('tbody')

    rows = table_body.find_all('tr')
    cellnames = [ "cellID", "cellDesc", "cellStartDate", "cellStartTime", "cellEndTime" ]
    for row in rows:
            d = {}
            for cl in cellnames:
                td = row.find('td', attrs={"class":cl})
                if td:
                    d[cl] = td.text.strip()
            if d:
                data.append(d)

    return json.dumps(data)

def fetch_future_confs():
    """
    fetch future conference ids
    return a list of future conference ids
    for use with send_conf_emails for example
    """

    from bs4 import BeautifulSoup
    import json

    CONFS_URL = "https://new.epresence.grnet.gr/conferences"

    s, _ = start_session()

    # Now fetch the data
    rc = s.get(CONFS_URL)

    soup = BeautifulSoup(rc.text, 'html5lib')

    data = []
    table = soup.find('table', attrs={'class':'futureConferences'})
    for a in table.find_all('a'):
        href = a['href'].strip().split('/')[2]
        data.append(href)

    return data


def check_emails(emails, s):

    """
    find if given emails are present
    emails is a list
    s is the session (must be supplied, use start_session() e.g.)
    return a dict of { email: id } and a list of missing emails (you can feed it to add_missing_users() )
    """
    import re

    URL = "https://new.epresence.grnet.gr/conferences/conferenceAddUserEmail"

    userids = {}
    missing = []
    for email_item in emails:
        email = email_item.strip()

        data = {
            'email': email,
            'page': "1"
        }

        r = s.post(URL, data)
        if (len(r.json())==0):
            missing.append(email)
        else:
            # find the id:
            SEARCH_USER_URL = "https://new.epresence.grnet.gr/conferences/requestParticipant/"+email
            r = s.get(SEARCH_USER_URL)
            user_id = re.findall('assignUserID\(([0-9]+)\)', r.text, re.M)[0]

            userids[email] = user_id

    return userids, missing


def add_missing_users(emails, s, token, conf_id):
    """
    add the missing users to the epresence system
    checks whether they are internal or external based on their domain
    emails is a list, e.g returned value missing from check_emails()
    """

    ADD_MISSING_USER_URL='https://new.epresence.grnet.gr/users'
    ADD_MISSING_USER_DATA = {
    '_token' : token,
    'lastname' : '',
    'firstname' : '',
    'telephone' : '',
    'institution_id' : '',
    'department_id' : '',
    'new_institution' : '',
    'new_department' : '',
    'status' : '1',
    'creator_id' : '30',
    'conference_id' : conf_id,
    'specialUser' : 'conferenceUser',
    'role' : 'EndUser',
    'from' : 'https://new.epresence.grnet.gr/conferences/'+str(conf_id)+'/edit',
    'conferenceAddNewUser' : 'Αποθήκευση+χρήστη+και+εισαγωγή+στους+συμμετέχοντες',
    }

    sso_domains = get_sso_domains()

    for email in emails:

        ADD_MISSING_USER_DATA['email'] = email

        domain = '.'.join(d for d in email.split('@')[1].split('.')[-2:])
        if domain.lower() in sso_domains:
            ADD_MISSING_USER_DATA['state'] = 'sso'
        else:
            ADD_MISSING_USER_DATA['state'] = 'local'

        print(email, ADD_MISSING_USER_DATA['state'])

        response = s.post(ADD_MISSING_USER_URL, ADD_MISSING_USER_DATA)
        print(response)



def add_conference(confname, start_date, start_time, end_time, emails='', early=False):

    """
    Adds a new conference
    All parameters are mandatory except emails
    date format: dd-mm-yyyy
    time format: HH:mm
    end date is always start date
    adds myself by default (as H323)
    early=True to start 15 minutes earlier
    """

    from datetime import datetime, timedelta

    s, token = start_session()

    NEW_CONF_URL = "https://new.epresence.grnet.gr/conferences"
    HEADERS = {'Referer': 'https://new.epresence.grnet.gr/conferences/create'}

    print(confname)
    # read participant emails from stdin
    emails = read_emails()
    if ( len(emails) > 0 ):
        users_no = len(emails)
    else:
        users_no = 3

    if(early):
        start_datetime = datetime.strptime(start_time, "%H:%M")
        start_datetime_earlier = start_datetime - timedelta(minutes=15)
        start_time_earlier = str(start_datetime_earlier.hour)+":"+str(start_datetime_earlier.minute)
        start_time = start_time_earlier

    postdata = {
        '_token' : token,
        'users_no' : users_no,
        'users_h323' : '1',
        'users_vidyo_room': '0',
        'title' : confname,
        'institution_id' : '7',
        'department_id' : '772',
        'start_date' : start_date,
        'start_time' : start_time,
        'end_date' : start_date,
        'end_time' : end_time,
        'invisible' : '0',
        'desc' : '',
        'files' : '',
        'descEn' : '',
        'files' : '',
        'max_users' : '15',
        'max_h323' : '10',
        'max_vidyo_room' : '5',
        'max_duration' : '360'
    }

    r = s.post(NEW_CONF_URL, data=postdata, headers=HEADERS)
    conf_id = r.url.split('/')[4]

    # add me by default
    ADD_USER_URL='https://new.epresence.grnet.gr/conferences/assign_participant'
    ADD_USER_DATA = {
        'user_id': 30,
        'conference_id': conf_id,
    }

    ru = s.post(ADD_USER_URL, ADD_USER_DATA)

    # change me to h323
    DEVICECHANGE_USER_URL='https://new.epresence.grnet.gr/conferences/userConferenceDeviceAssign'
    ADD_USER_DATA['device'] = "H323"
    ru = s.post(DEVICECHANGE_USER_URL, ADD_USER_DATA)


    # now add requested emails too:
    if ( len(emails) > 0 ):

        userdict, missinglist = check_emails(emails, s)

        if ( len(userdict) > 0 ):
            for user_id in userdict.values():
                ADD_USER_DATA = {
                    'user_id': user_id,
                    'conference_id': conf_id,
                }

                ru = s.post(ADD_USER_URL, ADD_USER_DATA)

        print("ConfID: "+conf_id)
        print("Added: "+str(list(userdict.keys())))

        if (len(missinglist) > 0):
            print("Missing emails: "+ str(missinglist))
            print("adding them...")
            add_missing_users(missinglist, s, token, conf_id)

    return r


def json2ical(sdata):

    """
    Convert epresence conferences
    sdata: conference list in json format (returned from fetch_conf_list)
    returns a string, the iCal, to be written to a file e.g.

    """

    import json
    from icalendar import Calendar, Event, Alarm
    from datetime import datetime
    import pytz
    data = json.loads(sdata)

    if data:

        cal = Calendar()
        cal.add('prodid', '-//Gamisterous epresence ical generator//lala.la//')
        cal.add('version', '3.0')
        cal.add('X-WR-CALNAME', 'Τηλεδιασκέψεις')
        local = pytz.timezone("Europe/Athens")

        for dato in data:

            confid=dato["cellID"]
            desc=dato["cellDesc"]
            start=datetime.strptime(dato["cellStartDate"]+"-"+dato["cellStartTime"],"%d-%m-%Y-%H:%M")
            end=datetime.strptime(dato["cellStartDate"]+"-"+dato["cellEndTime"],"%d-%m-%Y-%H:%M")
            now = datetime.now()

            event = Event()
            event.add('SUMMARY', desc)
            event.add('DTSTART', local.localize(start))
            event.add('DURATION', end-start)
            event.add('DTEND', local.localize(end))
            event.add('DTSTAMP', datetime.now())
            event.add('URL', 'https://new.epresence.grnet.gr')
            event['UID'] = "conf"+confid+"@conferences"

            # add a reminder 30m earlier
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add('description', "Reminder")
            alarm.add("TRIGGER;RELATED=START", "-PT30M")
            event.add_component(alarm)

            cal.add_component(event)

        return cal.to_ical()


def confs2ical():
    confs = fetch_conf_list()
    ical = json2ical(confs)
    f = open('confs.ics', 'wb')
    f.write(ical)
    f.close()


def fetch_participant_ids(s, conf_id):
    """
    gets the participants ids needed to send the invitation mails
    returns a list of the ids
    """

    from bs4 import BeautifulSoup

    CONF_URL = "https://new.epresence.grnet.gr/conferences/"+str(conf_id)+"/edit"

    # Now fetch the data
    rc = s.get(CONF_URL)

    soup = BeautifulSoup(rc.text, 'html5lib')

    data = []

    table = soup.find('table', attrs={'id':'participantsTable'})
    table_body = table.find('tbody')
    inputs = table_body.find_all('input', attrs={'class':'check'})
    for i in inputs:
        data.append(i.get("value"))

    return data


def send_conf_emails(conf_id):
    """
    sends the invitation mails for the given conference id
    """

    SEND_EMAIL_URL='https://new.epresence.grnet.gr/conferences/sendParticipantEmail'

    s, token = start_session()

    SEND_EMAIL_DATA = {
    '_token' : token,
    'conference_id' : conf_id,
    }

    ids = fetch_participant_ids(s, conf_id)

    for userid in ids:
        SEND_EMAIL_DATA["participants["+str(userid)+"]"] = userid

    print(SEND_EMAIL_DATA)

    r = s.post(SEND_EMAIL_URL, data=SEND_EMAIL_DATA)
    print(r)


def main():

    print("Begin")

    #add_conference('test conference name', '25-06-2018', '14:00', '15:30')

    confs2ical()

if ( __name__ == "__main__" ):
    main()

