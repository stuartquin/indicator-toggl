import pygtk
pygtk.require('2.0')
import gtk
import glib
import appindicator
import urllib2
import base64
import json
import time
import sys
import pynotify

class Config ():
    
    def __init__(self):
        self.ICON = "distributor-logo"


class AppIndicator (object):

    def __init__(self):
        self.ind = appindicator.Indicator("Toggl Indicator",
            config.ICON, appindicator.CATEGORY_COMMUNICATIONS)
        self.ind.set_status (appindicator.STATUS_ACTIVE)


class TogglInterface():

    def __init__(self):
        self.taskList        = dict()
        self.activeTask      = None

        # Used to calculate how many tabs are needed for each task
        self.longest         = 0

        # This stuff needs read from config
        self.REFRESH_TIME    = 10
        self.TOTAL_DISPLAYED = 6
        self.API_KEY         = sys.argv[1]

        self.notify = NotificationHandler()

    # Makes a request to Toggl API, retrives info and re-draws applet
    #
    def update_task_info(self, ind):

        print "update_tasks +"
        prevActiveTask  = self.activeTask
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

        # Pass to the NotificationHandler to decide wheter or not to show libnotify
        self.notify.show_task(self.activeTask)

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
        self.billable    = "false"
        self.startTime   = ""


    def parse_task(self, task):
        self.description = task["description"]
        self.id          = task["id"]
        self.duration    = task["duration"]
        self.billable    = task["billable"]
        self.startTime   = task["start"]
        self.project_id  = -1

        try:
            proj            = task["project"]
            self.project    = proj["client_project_name"]
            self.project_id = proj["id"]
        except KeyError:
            print "Warn: No project for "+self.description

        if self.duration < 0:
            self.duration = time.time() + task["duration"]
            self.active   = True

    def on_click(self, server,data=None):
        if self.project_id > -1:
            project = "\"project\":{\"id\":"+str(self.project_id)+"},"
        else: 
            project = ""

        currentTime = time.strftime("%Y-%m-%dT%H:%M:%S+01:00", time.gmtime())

        if self.billable:
            billable = "true"
        else:
            billable = "false"


        # Stop task
        print "{\"task\":{\"billable\":"+billable+",\"description\":\""+self.description+"\",\"start\":\""+self.startTime+"\",\"duration\":"+str(self.duration)+"}}"
        #"http://www.toggl.com/api/v3/tasks/"+self.id+".json"

        # Create task
        print "{\"task\":{\"billable\":"+billable+",\"description\":\""+self.description+"\","+project+"\"start\":\""+currentTime+"\", \"duration\":-1301472911,\"created_with\":\"Toggl Indicator\"}}"
        # http://www.toggl.com/api/v3/tasks.json


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

        spacing="\t"
        
        if longest == dl:
            return spacing

        moreSpace = True
        while moreSpace==True:
            spacing += "\t"
            diff -= 4

            if diff < 4:
                moreSpace = False

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
    
    def on_click_create_task(self, server,data=None):
        taskWindow = CreateTaskWindow()

    def render(self, menu):

        cItem = gtk.MenuItem("Create Task")
        cItem.connect("activate", self.on_click_create_task)

        pItem = gtk.MenuItem("Preferences")
        pItem.connect("activate", self.on_click_preferences)

        # Create a new menu item
        eItem = gtk.MenuItem("Exit")
        eItem.connect("activate", self.on_click_exit)

        # Add to menu
        menu.append(gtk.SeparatorMenuItem())
        menu.append(cItem)
        menu.append(pItem)
        menu.append(eItem)
        
class NotificationHandler:

    def __init__(self):
        self.prevId          = -1
        self.prevTime        = 0
        self.TIMEOUT         = 5
        # Show a notification every 15 mins
        self.NOTIFY_INTERVAL = 900

        try:
            if pynotify.init("Toggl Indicator App"):
                self.isAvailable = True
            else:
                self.isAvailable = False
                print "Error: There was a problem initializing the pynotify module"
        except:
                print "Error: You don't seem to have pynotify installed"

    def show_message(self, title, message = ""):
        if self.isAvailable:
            n = pynotify.Notification(title, message, config.ICON)
            n.set_timeout(self.TIMEOUT)
            n.show()

    def show_task(self, task):

        if time.time() - self.prevTime > self.NOTIFY_INTERVAL:
            self.prevId = -1

        if task:
            if self.prevId != task.id:
                self.show_message(task.description + " ("+task.get_time_str()+")", task.project)
                self.prevId   = task.id
                self.prevTime = time.time()


class CreateTaskWindow:

    def __init__(self):
        try:
            import pygtk
            pygtk.require("2.0")
        except:
            print "FAILS"
            pass
            
        try:
            import gtk
            import gtk.glade
        except:
            sys.exit(1)

        self.widgetTree = gtk.glade.XML("CreateTask.glade")
        
        dic = { 
            "on_click_create_btn" : self.on_click_create_btn,
            "on_click_cancel_btn" : self.on_click_cancel_btn
        }

        self.widgetTree.signal_autoconnect( dic )

    def on_click_cancel_btn(self, widget):
        window = self.widgetTree.get_widget("mainWindow")
        window.destroy()

    def on_click_create_btn(self, widget):
        taskField = self.widgetTree.get_widget("taskField")
        print taskField.get_text()






config    = Config()
indicator = AppIndicator()
toggl     = TogglInterface()

# Kicks off the application
toggl.update_task_info(indicator.ind)
gtk.main()
