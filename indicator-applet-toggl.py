import pygtk
pygtk.require('2.0')
import gtk
import glib
import appindicator
import urllib2
import base64
import json
import simplejson
import time
import sys
import pynotify

class Config ():

    def __init__(self):
        self.ICON = "distributor-logo"
        if len(sys.argv) > 2:
            self.DEBUG = True
        else:
            self.DEBUG = False

    def debug(self, msg):
        if self.DEBUG:
            print msg



class AppIndicator (object):

    def __init__(self):
        self.ind = appindicator.Indicator("Toggl Indicator",
            config.ICON, appindicator.CATEGORY_COMMUNICATIONS)
        self.ind.set_status (appindicator.STATUS_ACTIVE)
        
        menu        = gtk.Menu()
        menu.add(gtk.MenuItem("Loading..."))
        menu.show_all()
        self.ind.set_menu(menu)


class TogglInterface():

    def __init__(self):
        self.taskList        = dict()
        self.projectList     = None
        self.clientList      = None
        self.activeTask      = None

        # Used to calculate how many tabs are needed for each task
        self.longest         = 0

        # This stuff needs read from config
        self.REFRESH_TIME    = 10
        self.TOTAL_DISPLAYED = 6
        self.API_KEY         = sys.argv[1]
        
        # Only update the list of projects every minute
        self.PROJECT_REFRESH = 60

        self.notify = NotificationHandler()

        # Kicks off the application
        glib.timeout_add_seconds(1, self.update_task_info, indicator.ind)

        # Don't get list of projects immediatley, allows the app to start quicker
        glib.timeout_add_seconds(2, self.get_projects)

    # Makes a request to Toggl API, retrives info and re-draws applet
    #
    def update_task_info(self, ind, doTimeout = True):

        config.debug( "update_tasks +" )
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

        # Show currently active task
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

        if doTimeout:
            glib.timeout_add_seconds(self.REFRESH_TIME, self.update_task_info, ind)

        config.debug("update_tasks -")
    
    # Makes a request to the supplied URL
    # sets authorisation headers and returns the contents of "data" element in response
    #
    def make_request(self, url, data = None, req_method = None):

        base64string = base64.encodestring('%s:%s' % (self.API_KEY,"api_token")).strip()
        req          = urllib2.Request(url)
        req.add_header("Authorization", "Basic %s" % base64string)

        if data != None:
            req.add_header("Content-Type","application/json")
            req.add_data(data)
        
        if req_method != None:
            req.get_method = lambda: req_method

        config.debug("make_request + URL: "+url+", DATA:"+str(data))

        response = urllib2.urlopen(req)
        result   = response.read()

        output    = json.loads( result )
        return output["data"]

    # Creates a task, arguments can either be an existing task object or
    # string definition of a new task including project and client
    #
    def create_task(self, task, proj=None):

        project  = ""
        billable = "false"

        if isinstance(task, TogglTask):
            if task.billable:
                billable = "true"

            description = task.description

            if task.project_id > -1:
                project = "\"project\":{\"id\":"+str(task.project_id)+"},"
        else:
            if proj != "None":
                project = "\"project\":{\"id\":"+str(self.projectList[proj].id)+"},"
            description = task

        currentTime = time
        duration    = str(int(currentTime.time()))
        startTime   = time.strftime("%Y-%m-%dT%H:%M:%S+01:00", currentTime.gmtime())

        self.make_request("http://www.toggl.com/api/v3/tasks.json", "{\"task\":{\"billable\":"+billable+",\"description\":\""+description+"\","+project+"\"start\":\""+startTime+"\", \"duration\":-"+duration+",\"created_with\":\"Toggl Indicator\"}}")

        self.update_task_info(indicator.ind, False)

    # Stops a currently running
    #
    def stop_task(self, task):

        project  = ""
        billable = "false"
    
        if task.billable:
            billable = "true"

        self.make_request("http://www.toggl.com/api/v3/tasks/"+str(task.id)+".json", "{\"task\":{\"billable\":"+billable+",\"description\":\""+task.description+"\",\"start\":\""+task.startTime+"\",\"duration\":"+str(int(task.duration))+"}}", "PUT")

        self.update_task_info(indicator.ind, False)




    # Fetches a list of projects from toggl
    #
    def get_projects(self):
        config.debug("get_projects +")

        self.projectList = dict()
        projects  = self.make_request("http://www.toggl.com/api/v3/projects.json", None)

        for p in projects:
            project = TogglProject()
            project.parse_project(p)
            self.projectList[p["client_project_name"]] = project

        glib.timeout_add_seconds(self.PROJECT_REFRESH, self.get_projects)

        config.debug("get_projects -")

    # Makes HTTP request to server to fetch current and recent tasks
    # Need some way of optimising this, shouldnt create TogglTask for every entry
    #
    def get_tasks(self):

        tasks  = self.make_request("http://www.toggl.com/api/v3/tasks.json", None)

        for t in tasks:
            task = TogglTask()
            task.parse_task(t)
            self.taskList[t["id"]] = task

        return self.taskList


# Object representations of projects and clientsCombo
#
class TogglProject:

    def __init__(self):
        self.client_project_name = ""
        self.billable = "false"
        self.id = -1
    
    def parse_project(self, project):
        self.client_project_name = project["client_project_name"]
        self.id                  = project["id"]
        self.billable            = project["billable"]


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
            config.debug("Warn: No project for "+self.description)

        if self.duration < 0:
            self.duration = time.time() + task["duration"]
            self.active   = True

    def on_click(self, server,data=None):

        # Stop task
        if self.active:
            toggl.stop_task(self)
        else:
            # Create a new copy of this task, making it active
            toggl.create_task(self)
       

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
            config.debug(self.description + ":" + spacing + ":" + str(dl) + ":" + str(longest))
            return spacing

        moreSpace = True
        while moreSpace==True:
            spacing += "\t"
            diff    -= 4

            if diff <= 1:
                moreSpace = False

        config.debug(self.description + ":" + spacing + ":" + str(dl) + ":" + str(longest))

        return spacing


# Manages additional option shown at bottom of MenuItem
#
class Options:

    def __init__(self):
        config.debug("Init Options")
        
    def on_click_open_toggl(self, server, data=None):
        import webbrowser
        webbrowser.open("https://www.toggl.com/tasks")

    def on_click_preferences(self, server,data=None):
        print "Options"

    def on_click_exit(self, server,data=None):
        sys.exit(1)
    
    def on_click_create_task(self, server,data=None):
        taskWindow = CreateTaskWindow()

    def render(self, menu):

        cItem = gtk.MenuItem("Create Task")
        cItem.connect("activate", self.on_click_create_task)
        
        tItem = gtk.MenuItem("Open Toggl")
        tItem.connect("activate", self.on_click_open_toggl)

        pItem = gtk.MenuItem("Preferences")
        pItem.connect("activate", self.on_click_preferences)

        # Create a new menu item
        eItem = gtk.MenuItem("Exit")
        eItem.connect("activate", self.on_click_exit)

        # Add to menu
        menu.append(gtk.SeparatorMenuItem())
        menu.append(cItem)
        menu.append(tItem)
    
        menu.append(gtk.SeparatorMenuItem())
        menu.append(pItem)
        menu.append(eItem)
        
class NotificationHandler:

    def __init__(self):
        self.prevId          = -1
        self.prevTime        = 0
        self.TIMEOUT         = 3
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


# GUI window that allows user to Create a new task, includes project and client selection
#
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
        self.window     = self.widgetTree.get_widget("mainWindow")

        dic = { 
            "on_click_create_btn" : self.on_click_create_btn,
            "on_click_cancel_btn" : self.on_click_cancel_btn
        }

        self.widgetTree.signal_autoconnect( dic )
        
        self.set_project_combo()

    def set_project_combo(self):
        if toggl.projectList == None:
            toggl.get_projects()
            
            
        projectCombo = self.widgetTree.get_widget("projectsCombo")
        projects     = toggl.projectList
        keys         = sorted(projects)

        # Loop through keys in reverse oreder
        for i in keys:
            projectCombo.append_text(i)
            
        projectCombo.set_active(2)

    def on_click_cancel_btn(self, widget):
        self.window.destroy()

    def on_click_create_btn(self, widget):
        taskField    = self.widgetTree.get_widget("taskField")
        projectCombo = self.widgetTree.get_widget("projectsCombo")

        toggl.create_task(taskField.get_text(),projectCombo.get_active_text())
        
        self.window.destroy()

config    = Config()
indicator = AppIndicator()
toggl     = TogglInterface()

gtk.main()
