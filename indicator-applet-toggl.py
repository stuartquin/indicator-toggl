import pygtk
pygtk.require('2.0')
import gtk
import appindicator
import urllib2
import base64
import json

class AppIndicator (object):

    def __init__(self):
        self.ind = appindicator.Indicator("hello world client",
            "distributor-logo", appindicator.CATEGORY_COMMUNICATIONS)
        self.ind.set_status (appindicator.STATUS_ACTIVE)
        self.menu = gtk.Menu()
        item = gtk.MenuItem()

        toggl = TogglInterface()
        li    = toggl.get_tasks()

        for k, v in li.iteritems():
            lItem = gtk.MenuItem()
            lItem.connect("activate", self.on_click, k)
            lText = v.description

            if v.active:
                lText = "*" + v.description

            lItem.add(gtk.Label(lText))
            self.menu.append(lItem)

        # item.add(gtk.Entry())
        self.menu.show_all()
        self.ind.set_menu(self.menu)

    def on_click(self, server,data=None):
        print "Clicked Me!"+str(data[0])


class TogglInterface:

    def __init__(self):
        self.taskList = dict()

    def get_tasks(self):
        base64string = base64.encodestring('%s:%s' % ("bda544447018531daffbcde2febbc90f","api_token"))[:-1]
        req          = urllib2.Request("http://www.toggl.com/api/v3/tasks.json", None)

        req.add_header("Authorization", "Basic %s" % base64string)
        response = urllib2.urlopen(req)
        result   = response.read()

        output = json.loads( result )

        tasks = output["data"]

        for t in tasks:
            task = TogglTask()
            task.parse_task(t)
            self.taskList[t["id"]] = task

        return self.taskList

class TogglTask:

    def __init__(self):
        self.description = ""
        self.id          = -1
        self.active      = False

    def parse_task(self, task):
        self.description = task["description"]
        self.id          = task["id"]

        if task["duration"] < 0:
            self.active = True



indicator = AppIndicator()
gtk.main()
