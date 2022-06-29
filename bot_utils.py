from config import params
import os

# get / make the word
add_constant = params['keys']['add_constant']
add_position = params['keys']['add_position']
word = params['keys']['comp_p_word']
word = word + str(int(word[add_position]) + add_constant)


def make_and_start_systemd_bot_service(port_name, pword=word):
    port_params = params['active_services']['ports'][port_name]

    service = port_params['service']
    script = port_params['script']

    sysd_str = """[Unit]
Description=%s
StartLimitIntervalSec=5
StartLimitBurst=10
Wants=network.target
After=network.target

[Service]
User=paul
ExecStartPre=/bin/sleep 10
ExecStart=%s %s
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target""" % (service,
                                 script,
                                 port_name,
                                 )



    command = 'sudo chmod u+x ' + script \
              + '&& sudo echo "' + sysd_str + '" > /usr/lib/systemd/system/' + service + '.service' \
              + '&& sudo systemctl enable ' + service + '.service' \
              + '&& sudo systemctl start ' + service + '.service'

    _ = os.system('echo %s|sudo -S %s' % (pword, command))

    return None


def stop_and_remove_systemd_bot_service(port_name, pword=word):
    """
    """

    service = params['active_services']['down_ports'][port_name]['service']

    commands = []
    commands.append('sudo systemctl stop ' + service + '.service')
    commands.append('sudo systemctl disable ' + service + '.service')
    commands.append('sudo rm /usr/lib/systemd/system/' + service + '.service')  # remove job's unit file
    commands.append('sudo rm /etc/systemd/system/' + service + '.service')     # remove jobs
    commands.append('sudo systemctl daemon-reload')
    commands.append('sudo systemctl reset-failed')

    for command in commands:
        # try:
        _ = os.system('echo %s|sudo -S %s' % (pword, command))
    # except:
    #     print(5*('STOP AND REMOVE JOB: command failed ---- ' + command + '\n'), flush=True)

    return None