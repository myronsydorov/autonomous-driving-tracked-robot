import pygame
import socket
import sys
import time
import os

SERVER_IP = "192.168.0.115"   # IP des Servers anpassen
SERVER_PORT = 6003        # Port aus motor_tcp_server.py

def send_command(sock, command):
    try:
        sock.sendall((command + "\n").encode('utf-8'))
    except Exception as e:
        print(f"[FEHLER] Senden fehlgeschlagen: {e}")
        return False
    return True
def rechts_links(sock, value):
    if value < 0:
        return 
def main(stop_event=None):
    # Verbindung aufbauen
    print(f"Verbinde mit Motorserver unter {SERVER_IP}:{SERVER_PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))
        print("[INFO] Verbindung erfolgreich hergestellt.")
        greeting = sock.recv(1024).decode('utf-8')
        print(f"[SERVER] {greeting.strip()}")
    except Exception as e:
        print(f"[FEHLER] Verbindung fehlgeschlagen: {e}")
        return

    # Pygame initialisieren
    pygame.init()
    pygame.joystick.init()
    tastatur = False

    if pygame.joystick.get_count() == 0:
        print("Kein Controller gefunden.")
        print("Tastaturfallback findet statt.")
        tastatur = True
        os.environ['SDL_VIDEO_WINDOW_POS'] = "-1000,-1000" # Fensterposition nach Timbuktu verschieben
        pygame.display.set_mode((100, 100))  # Pygame beötigt kleines Fenster um Tastatureingaben anzunehmen
        # FENSTER MUSS IM FOKUS SEIN ---> IN README ERWÄHNEN!!!
    else:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"Controller verbunden: {joystick.get_name()}")

    try:
        # Zuweisung vor Schleife im Falle, dass Tastatur
        Throttle = 0.0
        Direction = 0.0
        while not(stop_event and stop_event.is_set()):
            pygame.event.pump()

            if (tastatur):
                keys = pygame.key.get_pressed()

                # In der Schleife (statt direkter Zuweisung):
                acceleration = 0.03  # Schrittgröße pro Frame
                deceleration = 0.05  # Rückgang pro Frame

                # Smooth Throttle
                if keys[pygame.K_w]:
                    Throttle = min(Throttle + acceleration, 0.5)
                elif keys[pygame.K_s]:
                    Throttle = max(Throttle - acceleration, -0.5)
                else:
                    # automatisch in Richtung 0 zurück
                    if Throttle > 0:
                        Throttle = max(Throttle - deceleration, 0.0)
                    elif Throttle < 0:
                        Throttle = min(Throttle + deceleration, 0.0)

                # Smooth Direction
                if keys[pygame.K_a]:
                    Direction = min(Direction + acceleration, 0.5)
                elif keys[pygame.K_d]:
                    Direction = max(Direction - acceleration, -0.5)
                else:
                    # automatisch in Richtung 0 zurück
                    if Direction > 0:
                        Direction = max(Direction - deceleration, 0.0)
                    elif Direction < 0:
                        Direction = min(Direction + deceleration, 0.0)
                print(f"Throttle: {Throttle}, Direction: {Direction}")
            else:
                Throttle = -joystick.get_axis(1)  # linker Stick Y-Achse
                Direction = -joystick.get_axis(2) # rechter Stick Y-Achse

                # Deadzone um Stickdrift entgegenzuwirken
                if abs(Throttle) < 0.075:
                    Throttle = 0.0
                if abs(Direction) < 0.1:
                    Direction = 0.0


            
            if Throttle != 0.0 and Direction == 0:
                left_track = Throttle
                right_track = Throttle
            
            # falls kein Throttle aber lenkung soll es sich auf der stelle drehen
            elif Throttle == 0.0 and Direction != 0.0:
                left_track = -Direction *(0.5 if Direction < 0 else 1.0)
                right_track = Direction *(0.5 if Direction > 0 else 1.0)



            else: # Throttle != 0.0 and Direction != 0:
                
                if Throttle > 0:
                    max_slow = -0.5 * abs(Throttle)
                    slow_track = Throttle + (max_slow - Throttle) * abs(Direction) # Formel um lansamere der beiden Ketten zu steuern
                else:
                    max_slow = 0.5 * (-Throttle)
                    slow_track = Throttle + (max_slow - Throttle) * abs(Direction) # Formel um lansamere der beiden Ketten zu steuern

                if Direction < 0:
                    if slow_track < 0.0:
                        left_track = Throttle + 0.2 * (abs(slow_track))
                    else:
                        left_track = Throttle 
                    right_track = slow_track
                else:
                    left_track = slow_track

                    if slow_track < 0.0:
                        right_track = Throttle + 0.2 * (abs(slow_track))
                    else:
                        right_track = Throttle 
                    #right_track = Throttle + 0.2 * slow_track
                    
            # Begrenze Werte auf [-1, 1]
            left_track = max(-1.0, min(1.0, left_track))
            right_track = max(-1.0, min(1.0, right_track))

            # Werte senden
            send_command(sock, f"set:{left_track:.3f},{right_track:.3f}")

            time.sleep(0.1)  # etwas delay, um Flooding zu vermeiden

    except KeyboardInterrupt:
        print("Steuerung unterbrochen.")
    finally:
        if (not tastatur):
            joystick.quit()
        pygame.quit()
        sock.close()
        print("Verbindung geschlossen.")

if __name__ == "__main__":
    main()
