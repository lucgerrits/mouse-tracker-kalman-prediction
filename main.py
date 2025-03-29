import math
import time
import tkinter as tk
import threading
import numpy as np
from matplotlib import pyplot as plt
from filterpy.kalman import KalmanFilter
import signal
import argparse

root1 = None

class KalmanVelocityPredictor:
    def __init__(self):
        self.kf = KalmanFilter(dim_x=4, dim_z=2)  # [x, y, vx, vy] and measurements [x, y]
        self.dt = 0.2  # Fixed time step
        self.R = 5
        self.Q = 0.5

        # State transition matrix (models constant velocity)
        self.kf.F = np.array([[1, 0, self.dt, 0],
                               [0, 1, 0, self.dt],
                               [0, 0, 1, 0],
                               [0, 0, 0, 1]])
        
        # Measurement function (we observe position only)
        self.kf.H = np.array([[1, 0, 0, 0],
                               [0, 1, 0, 0]])
        
        # Covariance matrices
        self.kf.P *= 500  # High initial uncertainty
        self.kf.R = np.array([[self.R, 0], [0, self.R]])  # Increased measurement noise
        self.kf.Q = np.array([[self.Q, 0, 0, 0],
                               [0, self.Q, 0, 0],
                               [0, 0, self.Q, 0],
                               [0, 0, 0, self.Q]])  # Process noise
        
        self.kf.x = np.array([0, 0, 0, 0])  # Initial state
    
    def predict(self):
        self.kf.predict()
        return self.kf.x[:2]  # Return predicted position
    
    def update(self, x, y):
        self.kf.update([x, y])
        return self.kf.x

class MyObject:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.distance_traveled = 0
        self.kalman = KalmanVelocityPredictor()
        self.kalman.update(x, y)

    def cal_distance(self, x, y):
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def update_position(self, x, y):
        self.kalman.predict()   # Propagate the state, including velocity
        state = self.kalman.update(x, y)
        self.x, self.y, self.vx, self.vy = state
        distance = self.cal_distance(x, y)
        self.distance_traveled += distance


class Application(tk.Tk):
    def __init__(self, plot_enabled):
        tk.Tk.__init__(self)
        self.is_my_pointer_init = False
        self.my_pointer = MyObject(0, 0)
        self.geometry('500x600')
        self.bind('<Motion>', self.event_update)
        self.lock = threading.Lock()
        self.canvas = tk.Canvas(self, width=500, height=600, bg='white')
        self.canvas.pack()
        self.arrow = None  # Reference to the arrow object
        self.plot_app = PlotApplication(self)
        self.plot_app.plot_enabled = plot_enabled
        self.plot_app.start_plot()
    
    def event_update(self, event):
        with self.lock:
            if not self.is_my_pointer_init:
                self.my_pointer = MyObject(event.x, event.y)
                self.is_my_pointer_init = True
                return

            # Store the latest mouse coordinates for accurate arrow placement
            self.last_mouse_x, self.last_mouse_y = event.x, event.y

            self.my_pointer.update_position(event.x, event.y)
            print(f"Position: x={self.my_pointer.x:.2f}, y={self.my_pointer.y:.2f}, "
                f"Velocity=({self.my_pointer.vx:.2f}, {self.my_pointer.vy:.2f}) m/s")
            print(f"Distance traveled: {self.my_pointer.distance_traveled:.2f} meters")

            # Update the velocity plot
            if self.plot_app.plot_enabled:
                self.plot_app.update_velocity(self.my_pointer)

            # Draw the velocity arrow
            self.draw_velocity_arrow()


    def draw_velocity_arrow(self):
        if self.arrow:
            self.canvas.delete(self.arrow)

        scale_factor = 1.3
        end_x = self.last_mouse_x + self.my_pointer.vx * scale_factor
        end_y = self.last_mouse_y + self.my_pointer.vy * scale_factor

        self.arrow = self.canvas.create_line(
            self.last_mouse_x, self.last_mouse_y, end_x, end_y,
            arrow=tk.LAST, fill='red', width=2
        )

class PlotApplication:
    def __init__(self, master):
        self.master = master
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.velocity_plot = []
        self.time_elapsed = []
        self.lock = threading.Lock()
        self.plot_range = 50
        self.ax.clear()
        self.fig.canvas.draw()
        self.plot_enabled = False

    def update_velocity(self, my_pointer):
        if not self.plot_enabled:
            return
        velocity_mag = math.sqrt(my_pointer.vx ** 2 + my_pointer.vy ** 2)
        self.velocity_plot.append(velocity_mag)
        self.time_elapsed.append(time.time())

        # Use `after()` to update Matplotlib from Tkinter's main thread
        self.master.after(10, self._safe_update_plot)

    def _safe_update_plot(self):
        with self.lock:
            self.ax.clear()
            self.ax.plot(self.time_elapsed[-self.plot_range:], self.velocity_plot[-self.plot_range:], 'ro-')
            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Velocity (m/s)')
            self.ax.set_title('Velocity Over Time')
            self.ax.grid()
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()

    def start_plot(self):
        if not self.plot_enabled:
            return
        threading.Thread(target=plt.show, kwargs={'block': False}, daemon=True).start()

def signal_handler(sig, frame):
    global root1
    root1.destroy()
    plt.close('all')
    exit()

def main():
    global root1
    signal.signal(signal.SIGINT, signal_handler)
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--plot', action='store_true', help='Enable velocity plot')
    args = parser.parse_args()
    plot_enable=False
    if args.plot:
        plot_enable=True
    root1 = Application(plot_enable)
    root1.mainloop()

if __name__ == "__main__":
    main()
