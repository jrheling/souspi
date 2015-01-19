#
# Copyright 2014-2015 Joshua Heling <jrh@netfluvia.org>
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

import time

import Adafruit_CharLCD

from souspi import SousPiUI

class LCDUI(SousPiUI.SousPiUIBase): 
    """ User interface for a 16x2 LCD + keypad module.

        Expects a 5-button keypad (up/down/right/left/select) that can be controlled by
        the Adafruit_CharLCD class. https://www.adafruit.com/product/1109 was used for
        testing.
    
        The LCD main screen displays key operational data about the sous vide machine:
    
        ------------------
        |Curstate hhh:mm
        |TEM.PE/SET.PO
        ------------------    
    
        Where:
            Curstate : 9 or 16 chars describing the current state
                            - only 9 are available if the system is at temp.
            hhh:mm : the time (hrs and minutes) the water bath has been at the target temp
            TEM.PE : the current temperature
            SET.PO : the current setpoint (temperature target)
    
        From the main screen, the RIGHT/LEFT buttons navigate the user through a loop
        of menu options.  A given option can be selected with the SELECT key.  From the 
        menu, the UP/DOWN keys will return the user to the main screen.  If no choice is
        made within a configurable amount of time, the user is also returned to the main
        screen.
        
        Each menu option, once entered, allows the user to take and confirm some action
        impacting state of the system, and when complete returns to the place in the menu
        from which it was launched.
        
        Backlight color, if supported by the LCD, is also used to reflect status:
            red    : setpoint not set
            blue   : setpoint being set
            green  : bath is at temperature
            yellow : bath is heating up
    
    """

    (SELECT, LEFT, UP, DOWN, RIGHT) = (Adafruit_CharLCD.SELECT, Adafruit_CharLCD.LEFT, 
                Adafruit_CharLCD.UP,
               Adafruit_CharLCD.DOWN, Adafruit_CharLCD.RIGHT)
    buttons = (SELECT, LEFT, UP, DOWN, RIGHT)

    def __init__(self, backlight=True):
        """ Set up the LCD and the order of its menu options. 
        
            By default, use background color as another status indicator.  Set backlight
            to False to avoid this.
        """
        super(LCDUI, self).__init__()

        self.lcd = Adafruit_CharLCD.Adafruit_CharLCDPlate()

        """ The menu is a list of tuples ("label", handler).  The label is displayed in the
            loop of menu choices, and the handler method is called if that choice is selected.
        """
        self.menuitems = (
                          ["change setpoint", self.do_setpoint],
                          ["start/stop", self.do_start_stop],
                          ["about", self.do_about]
                         )
                    
        self._backlight = backlight
        self._menu_selection_timeout = 3  # in seconds

    def _message(self, arg):
        self.lcd.message(arg)

    def _get_button(self, timeout=2):
        """ Return the button being pressed, or None if no button was pressed in time. 
        
            This will block indefinitely if timeout is set to None
        """
        if timeout is not None:
            end_time = time.time() + timeout
        
        while True:
            for i in range(10):
                for b in self.buttons:
                    if self.lcd.is_pressed(b):
                        logging.debug("get_button sees %s pressed" % b)
                        # wait for release (and for pin to return to normal)
                        while self.lcd.is_pressed(b):
                            time.sleep(0.01)
                        return b
            # only check to timeout every 10 times through the busy loop
            if timeout is not None and time.time() - end_time > 0:
                    logging.debug("get_button timed out")
                    return None
            time.sleep(0.1)

    def _fmt_temp(self, arg, leadingZero = True):
        """ Return arg as string with at least 2 decimal digits.  By default 0-prepend 3 pre-point digits.
    
            Takes: number (float or int)
            Returns: string
    
            It really seems like there must be a way to do this with printf.
        """
        if leadingZero:  # return NNN.NN+
            rstr = "%03d" % arg + str(arg%1)[1:]
        else:            # return N+.NN+
            rstr = "%d" % arg + str(arg%1)[1:]
        
        try:
            dot_pos = rstr.index('.')
        except ValueError:
            # if there is no decimal part, add one
            rstr += ".00"  
        else:
            ## if there's just one digit in the decimal part, add a zero
            if (len(rstr) - dot_pos) < 3:
                rstr += "0"
        return rstr

    def _nav_left(self):
        """ Move the _cur_menu pointer "left" in the menu nav loop. """
        self._cur_menu -= 1
        if self._cur_menu < 0:
            self._cur_menu = len(self.menuitems) - 1

    def _nav_right(self):
        """ Move the _cur_menu pointer "right" in the menu nav loop. """
        self._cur_menu += 1
        if self._cur_menu >= len(self.menuitems):
            self._cur_menu = 0

    def _draw_menu_item(self):
        """ Display the menu label for the currently selected item. """
        self.lcd.clear()
        self._message(self.menuitems[self._cur_menu][0])

    def blank(self):
        """ Clear and darken the screen. """
        self.lcd.clear()
        self.lcd.set_backlight(0)

    def main_screen(self):
        """ Display the main screen, with current state values. """
        while True:
            self.status.refresh()
            self.lcd.clear()
            
            # set backlight color
            if self.status.error is True:
                self._message("   Controller   \n     error.")
                time.sleep(10)
            else:
                if self.status.running:
                    if self.status.setpoint is None:
                        self._screen_no_setpoint()
                    else:
                        if abs(self.status.temp - self.status.setpoint) <= self.at_temp_threshold:
                            self._screen_at_temp()
                        else:
                            self._screen_heating_up()
                else:
                    self._screen_not_running()

                b = self._get_button(15)
                if b == self.RIGHT:            
                    self.menu()
                elif b == self.LEFT:
                    self.menu()
    
    def _temp_line(self):
        if self.status.temp is not None:
            self._message("%s" % self._fmt_temp(self.status.temp, False))
        if self.status.setpoint is not None:
            self._message("/%s" % self._fmt_temp(self.status.setpoint, False)) 

    def _screen_no_setpoint(self):
        # red if we have no setpoint
        self.lcd.set_color(1.0, 0, 0)
        self._message("No target set.\n")            
        self._temp_line()
        
    def _screen_at_temp(self):
        # green if we're at temp
        self.lcd.set_color(0, 1.0, 0)        
        self._message("At temp.")
        if self.status.time_at_setpoint is not None:
            self._message("%s\n") % self.status.time_at_setpoint
        else:
            self._message("\n")
        self._temp_line()
    
    def _screen_heating_up(self):
        # yellow if we're heating up
        self.lcd.set_color(1.0, 1.0, 0)
        self._message("Heating up.\n")    
        self._temp_line()        

    def _screen_not_running(self):
        # white if not running
        self.lcd.set_color(1.0, 1.0, 1.0)
        self._message("Temp control off\n")    
        self._temp_line()        

    def menu(self):
        """ Show the navigable ring of menu options. """        
        self._cur_menu = 0
        keep_looping = True
        while (keep_looping):  
            self._draw_menu_item()
            b = self._get_button(self._menu_selection_timeout)
            if b is not None:
                if b == self.LEFT:
                    self._nav_left()
                elif b == self.RIGHT:
                    self._nav_right()
                elif b == self.SELECT:
                    logging.debug("calling handler for menu item %s" % self.menuitems[self._cur_menu][0])
                    self.menuitems[self._cur_menu][1]()   # call handler for the current menu item
                    keep_looping = False
                else:
                    keep_looping = False             # leave menu if UP or DOWN are pressed
            else:
                # leave menu if no button is pressed in time
                keep_looping = False
    
    """ By convention, the menu actions are do_*.  Each should explicitly confirm its action. """

    def do_start_stop(self):
        """ Toggle PID state. """

        self.lcd.clear()

        self._message("Controller %s\n" % ("on" if self.status.running else "off"))
        self._message("SELECT to %s." % ("stop" if self.status.running else "start"))
        b = self._get_button(None)
        if b == self.SELECT:
            if self.status.running:
                self.stop()
            else:
                self.start()
                ## if we don't have water, the start attempt will fail - tell the user
                ##
                ## it is odd that we do this here rather than tell the user before they try to start
                ##  in the first place.  There is an underlying issue (to be fixed) wherein the SousPi
                ##  object doesn't update its "in_water" status when not running.
                self.status.refresh()
                if self.status.in_water is False:
                    self.lcd.clear()
                    self.lcd.set_cursor(0,0)
                    self._message("Can't start\nwithout water.")
                    self._get_button(20)
                    return
                
        self.status.refresh()
        
    def do_setpoint(self):
        """ Allow the user to set a new setpoint.
        
            Setpoint values are shown as three digits before the decimal, and two after.  Each digit
            get changed individually, and the new value must be explicitly confirmed in order to
            take effect.
        """
        retry = True
        while retry is True:
            retry = False
            self.lcd.clear()
            self.lcd.set_color(0, 0, 1.0)
        
            self._message("New setpoint:\n")
            if self.status.setpoint is not None:
                sp_str = self._fmt_temp(self.status.setpoint)
            else:
                sp_str = "000.00"
            dot_pos = 3  # we need to skip the dot when navigating around the string

            self.lcd.blink(True)
            # note: set_curson takes col, row - both are 0-indexed

            # use blinky cursor to indicate which char is selected for change
            # LEFT/RIGHT select which char we're changing, 
            # UP/DOWN change them
            sel_char = 0
        
            while (True):
                self.lcd.set_cursor(0,1)
                self._message(sp_str)
                self.lcd.set_cursor(sel_char,1)

                b = self._get_button(None)
                if b == self.SELECT:
                    ## if the setpoint hasn't been changed, this is basically an escape function
                    ## if it has been changed, it's a confirmation step
                    new_sp = float(sp_str)
                    if (new_sp == self.status.setpoint):
                        break
                
                    self.lcd.set_cursor(7,1)
                    self._message("Set?")
                    confb = self._get_button(None)
                    if confb == self.SELECT:
                        self.change_setpoint(float(sp_str))
                        self.status.refresh()
                        break
                    else:
                        self.lcd.set_cursor(0,0)
                        self._message("Up to cancel\nDown to retry")
                        cancelretry = self._get_button(None)
                        if cancelretry == self.UP:
                            break
                        elif cancelretry == self.DOWN:
                            # reset to inital state
                            retry = True
                            break
                elif b == self.RIGHT:
                    sel_char += 1
                    if sel_char == dot_pos:
                        sel_char += 1
                    if sel_char > len(sp_str) - 1:
                        sel_char = len(sp_str) - 1
                elif b == self.LEFT:
                    sel_char -= 1
                    if sel_char == dot_pos:
                        sel_char -= 1
                    if sel_char < 0:
                        sel_char = 0
                elif b == self.UP:
                    c = int(sp_str[sel_char])
                    c += 1
                    if c == 10:
                        c = 0
                    newstr = sp_str[:sel_char] + str(c) + sp_str[sel_char+1:]
                    sp_str = newstr
                elif b == self.DOWN:
                    c = int(sp_str[sel_char])
                    c -= 1
                    if c == -1:
                        c = 9
                    newstr = sp_str[:sel_char] + str(c) + sp_str[sel_char+1:]
                    sp_str = newstr

        self.lcd.blink(False)
            
        
    def do_about(self):
        self.lcd.clear()
        self._message("proto UI v0.1")
        self._get_button(None)
