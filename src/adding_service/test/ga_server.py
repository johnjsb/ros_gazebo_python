# producer

import copy 
import json
import zmq
 
import random
import rospy
 
import threading
 
class SenderThread(threading.Thread):
    def __init__(self, threadID, socket, genomes):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.socket = socket
        self.data = genomes
 
    def run(self):
        #print("\t\t\t\tStarting "+str(self.threadID))
        self.send_data()
        #print("\t\t\t\tExiting "+str(self.threadID))
 
    def send_data(self):
        """ Send data to worker processes. 
 
        Args:
            socket: socket to send the data out on.
                - Persistant throughout execution for now.
        """
        for i in self.data:
            msg = json.dumps(i)
            #print(msg)
            self.socket.send(msg)
 
class GACommunicator(object):
    """ Class to handle setting up the sockets and sending/receiving genome data. """

    def __init__(self):
        """ Initialize the socket for data. """

        # Setup the socket to send data out on.
        context = zmq.Context()
        self.socket = context.socket(zmq.PUSH)
        #socket.setsockopt(zmq.LINGER, 0)    # discard unsent messages on close
        self.socket.bind('tcp://127.0.0.1:5000')
 
        # Setup the socket to read the responses on.
        self.receiver = context.socket(zmq.PULL)
        self.receiver.bind('tcp://127.0.0.1:5010')

    def __del__(self):
        """ Close the sockets. """
        print("Closing Socket")
        self.socket.close()
        self.receiver.close()

    def send_genomes(self,genomes):
        """ Send the genomes through the sender thread to workers. 

        Args:
            genomes: list of genomes to send out.

        Returns:
            list of results containing the genome id and fitness
        """

        return_data = []

        # Start a thread to send the data.
        sendThread = SenderThread(1, self.socket, genomes)

        sendThread.start()
 
        # Read the responses on the receiver socket.
        i = len(genomes)
        while i > 0:
            data = json.loads(self.receiver.recv())
            return_data.append({'id':data['id'], 'fitness':data['fitness']})
            #return_data.append({'sum':data['sum'],'true_sum':data['a']+data['b']})
            i -= 1
         
        # Wait for the send thread to complete.
        sendThread.join()

        return return_data

class GA(object):

    def __init__(self):
        # Initialize the genomes with an id and randomly generated list of 20 floats under 1.0\
        self.num_genes = 20
        self.pop_size = 100

        self.genomes = [{'id':i,'genome':[random.random()*0.1 for j in range(self.num_genes)], 'fitness':-1.0} for i in range(self.pop_size)]
        self.id_map = {k:v for k,v in zip([x['id'] for x in self.genomes],[i for i in range(self.pop_size)])}
        self.elite_ind = -1
        self.ga_communicator = GACommunicator()

        self.child_id = self.pop_size

    def calculate_fitnesses(self):
        return_data = self.ga_communicator.send_genomes(self.genomes)
        max_fit = 0.0
        for rd in return_data:
            self.genomes[self.id_map[rd['id']]]['fitness'] = rd['fitness']
            if rd['fitness'] > max_fit:
                max_fit = rd['fitness']
                self.elite_ind = copy.deepcopy(self.genomes[self.id_map[rd['id']]])
        
        print(max_fit)

    def next_generation(self):
        """ Modify the population for the next generation. """
        child_pop = [copy.deepcopy(self.elite_ind)]

        # Perform tournament selection.
        for i in range(len(self.genomes)-1):
            tourn = random.sample(self.genomes,2)

            if tourn[0]['fitness'] > tourn[1]['fitness']:
                child_pop.append(copy.deepcopy(tourn[0]))
            else:
                child_pop.append(copy.deepcopy(tourn[1]))
            child_pop[-1]['id'] = self.child_id
            self.child_id += 1

        # Mutate one gene in the child genomes.
        for i in child_pop[1:len(child_pop)]:
            i['genome'][random.randint(0,len(i['genome'])-1)] = random.random()

        self.genomes = child_pop
        self.id_map = {k:v for k,v in zip([x['id'] for x in self.genomes],[i for i in range(self.pop_size)])}

# Initialize and execute the program.
ga = GA()

# TODO: Implement check for workers before sending data.
# TODO: Change messages so they persist while waiting for workers?
rospy.wait_for_service("/adder0/adder_transporter/get_loggers")

for i in range(100):
    ga.calculate_fitnesses()
    ga.next_generation()

 
# TODO: Auto-detect when workers are ready?
# TODO: Change messages so they persist waiting for workers?
#print("Press Enter when the workers are ready: ")
#_ = raw_input()



