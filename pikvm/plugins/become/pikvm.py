from ansible.plugins.become import BecomeBase
from ansible.errors import AnsibleError
import shlex

class BecomeModule(BecomeBase):
    name = "remount"
    # No interactive prompt or password handling needed (assumes root or passwordless access)

    def build_become_command(self, cmd, shell):
        # Initialize base settings (generate unique success marker, etc.)
        super(BecomeModule, self).build_become_command(cmd, shell)
        if not cmd:
            return cmd

        # Ensure we are only trying to become root (required for mount operations)
        user = self.get_option("become_user") or "root"
        if user not in ("root", ""):
            raise AnsibleError("The 'remount' become plugin only supports becoming root.")

        # Prepare a unique success sentinel (provided by BecomeBase)
        sentinel = self.success  # e.g. "BECOME-SUCCESS-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

        # Construct shell script to remount partitions RW, run the command, then remount RO
        script = (
            f'echo {sentinel}; '                     # indicate privilege escalation success
            'successMounts=""; '
            'for m in / /boot; do '          # loop through target mount points
            '    if [ -d "$m" ]; then '
            '        if mountpoint -q "$m"; then '   # only attempt if $m is a mount point
            '            if ! mount -o remount,rw "$m"; then '  
            '                echo "Failed to remount $m as read-write" >&2; '
            '                for n in $successMounts; do mount -o remount,ro "$n"; done; '
            '                exit 1; '
            '            fi; '
            '            successMounts="$m $successMounts"; '  # record successful remounts
            '        fi; '
            '    fi; '
            'done; '
            f'( {cmd} ); '                            # execute the original command in a subshell
            'ret=$?; '                                # capture the command’s exit code
            'revert_failed=0; '
            'for n in $successMounts; do '           # revert each successfully remounted FS
            '    if ! mount -o remount,ro "$n"; then '
            '        echo "Failed to remount $n as read-only" >&2; '
            '        revert_failed=1; '
            '    fi; '
            'done; '
            'if [ $ret -eq 0 ] && [ $revert_failed -ne 0 ]; then '  # command ok but revert failed
            '    exit 1; '
            'fi; '
            'exit $ret; '                             # exit with the original command’s status
        )

        # Use /bin/sh to run our constructed script
        shell_exe = self.get_option("become_exe") or "/bin/sh"
        return f'{shell_exe} -c {shlex.quote(script)}'

