import time

INTERVAL = 0.2


class CpuLoad:

    def __init__(self):
        print("created CpuLoad")

    def getTimeList(self):
        """
        Fetches a list of time units the cpu has spent in various modes
        Detailed explanation at http://www.linuxhowtos.org/System/procstat.htm
        """
        with open("/proc/stat", "r") as f:
            cpuStats = f.readline()
        columns = cpuStats.replace("cpu", "").split(" ")
        return list(map(int, [_f for _f in columns if _f]))

    def deltaTime(self, interval):
        """
        Returns the difference of the cpu statistics returned by getTimeList
        that occurred in the given time delta
        """
        timeList1 = self.getTimeList()
        time.sleep(interval)
        timeList2 = self.getTimeList()
        return [(t2 - t1) for t1, t2 in zip(timeList1, timeList2)]

    def getCpuLoad(self):
        """
        Returns the cpu load as a value from the interval [0.0, 1.0]
        """
        dt = list(self.deltaTime(INTERVAL))
        idle_time = float(dt[3])
        total_time = sum(dt)
        load = 1 - (idle_time / total_time)
        return load


cpuLoad = CpuLoad()

print("cpu: %s" % cpuLoad.getCpuLoad())
