# $Id$
import sys, time


class Meter(object):
    def __init__(self, percentages=None, num_items=0, start_now=False):
        # The percentages of items at which to update the progress meter
        self.percentages = percentages or \
                           [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90]
        while self.percentages[-1] >= 100: self.percentages.pop()
        self.percentages.append(100)
        self.per_len = len(self.percentages)

        # Reset these after last update (i.e., at 100%)
        self.num_items = num_items
        self.per_idx = -1
        self.update_points = None
        self.warned = False
        self.start_time = None

        self.setNumberOfItems(num_items)

        self.length = 6 + self.per_len

        if start_now:
            self.startTimer()
        
    def startTimer(self):
        if self.start_time:
            print "Progress Meter timer already started."
            return
        self.start_time = time.time()

    def setNumberOfItems(self, num_items):
        if not num_items or self.update_points: return
        self.num_items = num_items
        self.per_idx = 0
        self.update_points = [int(num_items * p * .01)
                              for p in self.percentages]

    def update(self, item_number):
        if not self.update_points:
            self.warn()
            return False

        # Update the progress meter if current item number is an update point
        if item_number == self.update_points[self.per_idx]:
            sys.stdout.write("\r%s" % (" " * self.length))

            # end marker
            sys.stdout.write("| Processing %s items\r" % self.num_items)

            # % done
            sys.stdout.write("%3s" % (self.percentages[self.per_idx]))
            
            self.per_idx+=1
            
            sys.stdout.write("%% |%s" % ("*" * self.per_idx))
            sys.stdout.flush()
            
            if item_number == self.update_points[-1]:
                self.printElapsedTime(item_number)
                self.reset()
            
            return True

        return False

    def printElapsedTime(self, last_item_number):
        """Print number of seconds since the timer was started (if it was)."""
        if self.start_time:
            elapsed_time = int(round(time.time() - self.start_time))
            units = "seconds"
            if elapsed_time > 59:
                elapsed_time = "%.2s" % (elapsed_time / 60.)
                units = "minutes"
            sys.stdout.write("| %s items took %s %s to process" % \
                (last_item_number, elapsed_time, units))

    def reset(self):
        self.num_items = 0
        self.per_idx = -1
        self.update_points = None
        self.warned = False
        self.start_time = None

    def warn(self):
        if self.warned: return
        self.warned == True
        print "Progress Meter was not initialized."


class Timer(object):
    """Super simple wall clock timer."""
    
    def __init__(self, start_now=False):
        """Create a new `Timer`, usually not started until `start` is called.
        
        ``start_now`` -- If set, start now instead of waiting for `start` to
        be called.
        
        """
        self.start_time = 0
        self.elapsed_time = 0
        self.paused = True        
        self.elapsed_time = 0
        if start_now:
            self.start()
    
    def start(self):
        """Start the timer.

        Starting is just a special case of unpausing where we reset the
        elapsed time.

        """
        if not self.paused:
            return
        self.elapsed_time = 0
        self.unpause()
        
    def stop(self):
        """Stop this timer and return the number of seconds elapsed."""
        self.pause()
        return self.elapsed_time

    def pause(self):
        """Pause this timer."""
        if self.paused:
            return        
        self.paused = True
        self.elapsed_time += (time.time() - self.start_time)

    def unpause(self):
        """Unpause this timer."""
        if not self.paused:
            return
        self.paused = False
        self.start_time = time.time()
