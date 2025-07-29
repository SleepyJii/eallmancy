shopt -s expand_aliases
source ~/.bashrc

#SIMPLESCRIPT_CMD="-o ConnectTimeout=3 -o StrictHostKeyChecking=no tmux new-session -d -s optuna_worker \"~/bitbucket_venvs/gputraining/bin/python3 ~/optuna_worker.py\""
#SIMPLESCRIPT_CMD="-o ConnectTimeout=3 -o StrictHostKeyChecking=no tmux new-session -d -s optuna_worker \"~/bitbucket_venvs/gputraining/bin/python3 ~/schcw_worker.py\""


#ISOWRK="./workkit/generalized_worker.py '/homes/jpk24/iso/tokenomic_adoption_simulator/distributed/simulation_job.py' --workingdir='/homes/jpk24/iso/tokenomic_adoption_simulator/' --backoff_min=1 --idle_backoff_min=15"
# SIMPLESCRIPT_CMD="-o ConnectTimeout=3 -o StrictHostKeyChecking=no tmux new-session -d -s optuna_worker \"$ISOWRK\""
# 
NODESCRIPT="/homes/jpk24/eallmancy/experiments/jobs/workkit_node.sh"
DAEMON_NODESCRIPT="-o ConnectTimeout=4 -o StrictHostKeyChecking=no tmux new-session -d -s eallminion \"$NODESCRIPT\""


SIMPLESCRIPT_CMD=$DAEMON_NODESCRIPT

#SIMPLESCRIPT_CMD="-o ConnectTimeout=4 -o StrictHostKeyChecking=no 'who && nvidia-smi'"
#SIMPLESCRIPT_CMD="-o ConnectTimeout=4 -o StrictHostKeyChecking=no tmux list-sessions"
#SIMPLESCRIPT_CMD="-o ConnectTimeout=3 -o StrictHostKeyChecking=no tmux kill-session -t optuna_worker "

# FIND MY SESSIONS AFTER CRASH
#SIMPLESCRIPT_CMD="-o ConnectTimeout=3 -o StrictHostKeyChecking=no who"

#SIMPLESCRIPT_CMD="echo \$(hostname)"

## roughly grabbed from https://www.imperial.ac.uk/computing/people/csg/facilities/lab/workstations/
prefix_count_list=(
## "texel,44" 

 "oak,38" 

# "perry,6" 
# "cedar,7" 

#"gpu,36" 

# "ash,41" 
# "beech,21" 

 "willow,20"  

# "vertex,22" 
# "ray,26" 
# "maple,10" 
# "curve,12" 
## "pixel,40"
)

# Loop through each prefix,count pair
for item in "${prefix_count_list[@]}"; do
    # Split the string on ',' to extract the prefix and count
    prefix=$(echo "$item" | cut -d',' -f1)
    count=$(echo "$item" | cut -d',' -f2)
    
    # Loop to define aliases for the current prefix up to the specified count
    for i in $(seq -f "%02g" 1 "$count"); do
	echo ""
	echo "${prefix}${i}"
        eval "${prefix}${i} $SIMPLESCRIPT_CMD"
	#sleep 1m
    done
done


