shopt -s expand_aliases
source ~/.bashrc



#NODESCRIPT="/homes/jpk24/eallmancy/experiments/jobs/workkit_node.sh"
#DAEMON_NODESCRIPT="-o ConnectTimeout=4 -o StrictHostKeyChecking=no tmux new-session -d -s eallminion \"$NODESCRIPT\""
#SIMPLESCRIPT_CMD=$DAEMON_NODESCRIPT

SIMPLESCRIPT_CMD="-o ConnectTimeout=4 -o StrictHostKeyChecking=no tmux list-sessions | grep eallminion || echo 'node down'"
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
        res=$(eval "${prefix}${i} $SIMPLESCRIPT_CMD" 2>1)
	echo "${prefix}${i} $res"

	#sleep 1m
    done
done


