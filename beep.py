from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep


@asm_pio()
def square_prog_tone_irq():
    label("restart")
    pull(noblock)
    # irq(clear, 4) 
    mov(x, osr) 
    mov(y, isr)
    
    #start loop
    #here, the pin is low, and it will count down y
    #until y=x, then put the pin high and jump to the next secion
    label("uploop")
    jmp(x_not_y, "skip_up")
    #nop()
    irq(4)
    jmp("down")
    label("skip_up")
    jmp(y_dec, "uploop")
    
    #mirror the above loop, but with the pin high to form the second
    #half of the square wave
    label("down")
    mov(y, isr)
    label("down_loop")
    jmp(x_not_y, "skip_down")
    #nop()
    irq(clear, 4) 
    jmp("restart")
    label("skip_down")
    jmp(y_dec, "down_loop")


@asm_pio(sideset_init=PIO.OUT_LOW)
def square_prog_volume_irq():
    pull(noblock) .side(0)
    mov(x, osr) # Keep most recent pull data stashed in X, for recycling by noblock
    set(y, 7)
    wait(0, irq, 4)
    label("pwmloop")
    jmp(x_not_y, "skip")
    nop()         .side(1)
    label("skip")
    jmp(y_dec, "pwmloop")

    
class PIOBeep:
    max_count_tone = 5000
    max_count_volume = 7
    freq_tone = 1000000
    freq_volume = 125000000
    
    def __init__(self, pin_id):
        self.pin = Pin(pin_id)
        self.tone_sm = StateMachine(2, square_prog_tone_irq, freq=self.freq_tone)
        self.volume_sm = StateMachine(3, square_prog_volume_irq, freq=self.freq_volume, sideset_base=self.pin)

        #pre-load the isr with the value of max_count
        self.tone_sm.put(self.max_count_tone)
        self.tone_sm.exec("pull()")
        self.tone_sm.exec("mov(isr, osr)")

    #note - based on current values of max_count and freq
    # this will be slightly out because of the initial mov instructions,
    #but that should only have an effect at very high frequencies
    def calc_pitch(self, hertz):
        return int( -1 * (((self.freq_tone/hertz) -20000)/4))
    
    def play_value(self, note_len, pause_len, val, volume):
        volume -= 1
        volume = min(volume, self.max_count_volume)
        volume = max(volume, -1)  # -1 is lowest value due to overloading int
                                  # (0 is 1/8th duty cycle) 
        self.tone_sm.active(1)
        self.tone_sm.put(val)
        self.volume_sm.active(1)
        self.volume_sm.put(volume)
        sleep(note_len)
        self.tone_sm.active(0)
        self.volume_sm.active(0)
        sleep(pause_len)
        self.pin.off()
        
    def play_tone(self, note_len, pause_len, pitch, volume):
        self.play_value(note_len, pause_len, self.calc_pitch(pitch), volume)
        
pio_beep = PIOBeep(22)
pio_beep.play_tone(1, 0, 1000, 8)
pio_beep.play_tone(1, 0, 1200, 4)
pio_beep.play_tone(4, 0, 1300, 1)
pio_beep.play_tone(1, 1, 5000, 0)

