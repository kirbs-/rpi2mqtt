# rpi2mqtt
Simplify interacting Raspberry Pi sensors and GPIO pins remotely via MQTT. Also integrates with Home Assistant. 
 

# Supported Devices
- Temperature/Humidity
    - DHT22/DHT11
    - One wire (DS18B20, MAX31850, etc)
    - BME280
- Binary
    - Generic reed switches
- Thermostat
    - HestiaPi
- Switch GPIO pins on/off. e.g. activate relay, LED, etc.


# Installation
1. `sudo pip install rpi2mqtt`
2. `rpi2mqtt --generate-config`
3. Update config.yaml. See configuration info.
    

# Configuration
### Setup MQTT
1. Open config.yaml.
2. Edit MQTT broker details
```yaml
# config.yaml
mqtt:
  host: example.com
  port: 8883
  ca_cert: '/path/to/example.com.crt'
  username: mqtt_user
  password: secure_password
  retries: 3
```
3\. add sensors to config.yaml
```yaml
# config.yaml
sensors:
  - type: dht22
    name: laundry_room_climate
    pin: 16
    topic: 'homeassistant/sensor/laundry_room_climate/state'
  - type: reed
    name: laundry_room_door
    pin: 24
    normally_open: true
    topic: 'homeassistant/sensor/laundry_room_climate/state'
```
3. Start rpi2mqtt
`rpi2mqtt -c /path/to/config.yaml`


### Install systemd service
4. `rpi2mqtt --install-service` and enter run user and absolute path to config.yaml
5. Enable and start service `sudo systemctl enable rpi2mqtt`
6. `sudo systemctl start rpi2mqtt`


