class Bandwidth(object):
    """
    Represent a Bandwidth object in multiple ways
    """
    def __init__(self, bw):
       self.raw = bw
       if isinstance(bw, str):
           # parse out Mbps, Gbps, Kbpbs etc
           self.bw = self.human_to_bandwidth_bps(bw)
       elif isinstance(bw, int):
           self.bw = bw
       elif isinstance(bw, float):
           self.bw = bw
       else:
           self.bw = 0

    def __str__(self):
       return str(self.bandwidth_bps_to_human(self.bw))

    def __repr__(self):
       return str(self.bandwidth_bps_to_human(self.bw))

    def __sub__(self, other):
        #print "SUB:", self.bw, other.bw
        if isinstance(self.bw, int) and isinstance(other.bw, int):
            return self.bw - other.bw
        if isinstance(self.bw, float) and isinstance(other.bw, float):
            #print "   floats__sub__", self.bw - other.bw
            return self.bw - other.bw
        return float(self.bw) - float(other.bw)


    def __add__(self, other):
        return self.bw + other.bw

    def __div__(self, other):
        if isinstance(self.bw, int) and isinstance(other.bw, int):
            if other.bw > 0:
                return self.bw / other.bw
            else:
                return 0
        if isinstance(self.bw, float) and isinstance(other.bw, float):
            if other.bw > 0.0:
                return self.bw / other.bw
            else:
                return 0.0
        return float(self.bw) / float(other.bw)

    def __mul__(self, other):
        return self.bw * other.bw

    def __eq__(self, other):
        return self.bw == other.bw

    def __lt__(self, other):
        return self.bw < other.bw

    def __le__(self, other):
        return self.bw <= other.bw

    def __gt__(self, other):
        return self.bw > other.bw

    def __ge__(self, other):
        return self.bw >= other.bw

    def human_to_bandwidth_bps(self,value):
        # strip whitespace
        value = value.strip()
        value = value.lower()
        if value[-3:] == 'bps':
            value = value[:-3].lower()
        # parse the last character for a bw multiplier
        if value[-1] == 'k':
            bw=float(value[:-1]) * 10**3
        elif value[-1] == 'm':
            bw=float(value[:-1]) * 10**6
        elif value[-1] == 'g':
            bw=float(value[:-1]) * 10**9
        else:
            bw=float(value)
        return bw

    def bandwidth_bps_to_human(self,value):
        """
		This function converts an in integer in BPS to a more human readable
		format using m or megabytes or g for gigabytes
		it returns a string
		"""
		# make sure value is an integer
        value = int(value)
		# check for g
        if value / 10.0**9 >= 1:
            value = str(value / 10.0**9) + "g"
        elif value / 10**6 >=1:
            value = str(value / 10.0**6) + "m"
        elif value / 10**3 >=1:
            value = str(value / 10.0**3) + "k"
        else:
            value = str(value)
        # Strip off any .0 values
        value = value.replace(".0", "")
        return value
