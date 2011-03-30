import pygtk
pygtk.require('2.0')
import gtk
import glib
import appindicator
import urllib2
import base64
import json
import threading

class AppIndicator (object):

    def __init__(self):
        self.ind = appindicator.Indicator("hello world client",
            "distributor-logo", appindicator.CATEGORY_COMMUNICATIONS)
        self.ind.set_status (appindicator.STATUS_ACTIVE)

        toggl = TogglInterface()
        toggl.update_task_info(self.ind)



class TogglInterface():

    def __init__(self):
        self.taskList        = dict()
        self.REFRESH_TIME    = 10
        self.TOTAL_DISPLAYED = 7


    # Makes a request to Toggl API, retrives info and re-draws applet
    #
    def update_task_info(self, ind):

        print "update_tasks +"

        # Make Call to Server, 
        # @todo: Needs error checking
        #
        tasks = self.get_tasks()
        keys  = sorted(tasks)

        menu = gtk.Menu()
        taskCount = 0

        # Loop through keys in reverse oreder
        for i in reversed(keys):

            task = tasks[i]

            lText = task.description
            if task.active:
                lText = "*" + task.description

            # Create a new menu item
            lItem = gtk.MenuItem(lText)
            lItem.connect("activate", task.on_click, task)

            # Add to menu
            menu.append(lItem)
            
            # Increase task count
            taskCount = taskCount+1
            if taskCount >= self.TOTAL_DISPLAYED:
                break


        # item.add(gtk.Entry())
        menu.show_all()
        ind.set_menu(menu)

        glib.timeout_add_seconds(self.REFRESH_TIME, self.update_task_info, ind)
        print "update_tasks -"

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

    def on_click(self, server,data=None):
        print "Clicked Me!"+str(data)



indicator = AppIndicator()
gtk.main()
