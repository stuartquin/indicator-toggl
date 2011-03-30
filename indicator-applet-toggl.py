import pygtk
pygtk.require('2.0')
import gtk
import glib
import appindicator
import urllib2
import base64
import json
import time

class AppIndicator (object):

    def __init__(self):
        self.ind = appindicator.Indicator("Toggl Indicator",
            "TogglDesktop", appindicator.CATEGORY_COMMUNICATIONS)
        self.ind.set_status (appindicator.STATUS_ACTIVE)

        toggl = TogglInterface()
        toggl.update_task_info(self.ind)



class TogglInterface():

    def __init__(self):
        self.taskList        = dict()
        self.activeTask      = None

        # Used to calculate how many tabs are needed for each task
        self.longest         = 0

        # This stuff needs read from config
        self.REFRESH_TIME    = 10
        self.TOTAL_DISPLAYED = 6
        self.API_KEY         = ""


    # Makes a request to Toggl API, retrives info and re-draws applet
    #
    def update_task_info(self, ind):

        print "update_tasks +"
        self.activeTask = None

        # Make Call to Server, 
        # @todo: Needs error checking
        #
        tasks = self.get_tasks()
        keys  = sorted(tasks)

        menu        = gtk.Menu()
        taskCount   = 0
        renderTasks = []

        # Loop through keys in reverse oreder
        for i in reversed(keys):

            task = tasks[i]
            # Keep track of longest item
            l = len(task.description)
            if l > self.longest:
                self.longest = l

            # Keep track of currently active task
            # Drops out of loop
            if task.active:
                self.activeTask = task
            else:
                renderTasks.append(task)

            # Increase task count
            taskCount = taskCount+1
            if taskCount >= self.TOTAL_DISPLAYED:
                break


        if self.activeTask:
            currentTitle = gtk.MenuItem("Current Task \t (Click to stop)")
            currentTitle.set_sensitive(False)

            # Add to menu
            menu.append(currentTitle)
            self.activeTask.render(menu, self.longest)
            menu.append(gtk.SeparatorMenuItem())

            # Add a title
            recentTitle = gtk.MenuItem("Recent Tasks \t (Click to continue)")
            recentTitle.set_sensitive(False)
            menu.append(recentTitle)

        # Render recent tasks
        for task in renderTasks:
            task.render(menu, self.longest)


        # Draw options
        options = Options()
        options.render(menu)


        menu.show_all()
        ind.set_menu(menu)

        glib.timeout_add_seconds(self.REFRESH_TIME, self.update_task_info, ind)
        print "update_tasks -"


    # Makes HTTP request to server to fetch current and recent tasks
    # Need some way of optimising this, shouldnt create TogglTask for every entry
    #
    def get_tasks(self):
        base64string = base64.encodestring('%s:%s' % (self.API_KEY,"api_token"))[:-1]
        req          = urllib2.Request("http://www.toggl.com/api/v3/tasks.json", None)

        req.add_header("Authorization", "Basic %s" % base64string)
        response = urllib2.urlopen(req)
        result   = response.read()

        output = json.loads( result )
        tasks  = output["data"]

        for t in tasks:
            task = TogglTask()
            task.parse_task(t)
            self.taskList[t["id"]] = task

        return self.taskList

# Created for every toggl task
#
class TogglTask:

    def __init__(self):
        self.description = ""
        self.id          = -1
        self.active      = False
        self.project     = ""
        self.duration    = -1

    def parse_task(self, task):
        self.description = task["description"]
        self.id          = task["id"]
        self.duration    = task["duration"]

        try:
            proj          = task["project"]
            self.project  = proj["client_project_name"]
        except KeyError:
            print "No project for "+self.description

        if self.duration < 0:
            self.duration = time.time() + task["duration"]
            self.active   = True

    def on_click(self, server,data=None):
        print "Clicked Me!"+str(data)

    def get_time_str(self):
        return time.strftime('%H:%M:%S', time.gmtime(self.duration) )

    def render(self, menu, longest):

        # Calculate how many tabs are required
        spacing = self.get_tabs_str(longest)

        # Create a new menu item
        lText = self.description + spacing + self.get_time_str() + "\n" + self.project
        lItem = gtk.MenuItem(lText)
        lItem.connect("activate", self.on_click)
        menu.add(lItem)


    # Performs some crazy calculations to determine amount of tabs needed for
    # perfect alignment
    #
    def get_tabs_str(self, longest):
        dl    = len(self.description)
        diff  = longest - dl

        diff  = diff -(dl%4)

        spacing   = "\t"
        numSpaces = diff/4

        if numSpaces == 0:
            if diff%4 > 0:
                numSpaces=1

        for i in range(0,numSpaces):
            spacing = spacing + "\t"

        return spacing

# Manages additional option shown at bottom of MenuItem
#
class Options:

    def __init__(self):
        print "Init Options"

    def on_click_preferences(self, server,data=None):
        print "Options"

    def on_click_exit(self, server,data=None):
        print "exit"

    def render(self, menu):

        pItem = gtk.MenuItem("Preferences")
        pItem.connect("activate", self.on_click_preferences)

        # Create a new menu item
        eItem = gtk.MenuItem("Exit")
        eItem.connect("activate", self.on_click_exit)

        # Add to menu
        menu.append(gtk.SeparatorMenuItem())
        menu.append(pItem)
        menu.append(eItem)

indicator = AppIndicator()
gtk.main()
