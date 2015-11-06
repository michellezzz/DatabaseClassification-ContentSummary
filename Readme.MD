----------------
a. Team Member

Xingying Liu(xl2493)
Moning Zhang(mz2499)

----------------
b. List of files

bing.py (the main program)
Root-diabetes.org.txt (sample output)
Health-diabetes.org.txt (sample output)
Root-fifa.com.txt (sample output)
Sports-fifa.com.txt (sample output)
Root.txt (original queries)
Computers.txt (original queries)
Health.txt (original queries)
Sports.txt (original queries)
Readme.MD (readme)

----------------
c. How to run the program

$ python python bing.py <BING_ACCOUNT_KEY> <t_es> <t_ec> <host>

Our account key: "OFzQIRuHcxWsxd0/QCQeUSvDsQOW/mVkEJygRt2rnUE"

----------------
d. Internal Design

We defined a Category class to store the information of a category. Including:

        self.children = []   -->  a list of child category
        self.label = label   --> the name of this category (root, computer ...)
        self.rules = rules   --> the queries for this category

With the Category class, we are able to build the category tree by reading the query files.

        def generate_tree(self, root_file):
        file = open(root_file)
        namelist = defaultdict(int)
        for eachline in file:
            item = eachline.strip().split()
            query = '%20'.join(item[1:len(item)])
            if item[0] not in namelist:
                namelist[item[0]] = []
            namelist[item[0]].append(query)
        for node in namelist:
            file_name = node +'.txt'
            child = Category(node, namelist[node])
            try:
                child.generate_tree(file_name)
            except Exception, e:
                child.children = []
            self.children.append(child)

Then,

Part 1  Database Classification

We do the classification in the function: classify. This function takes "category, database, t_ec, t_es, especificity_C" as input, and return the classification result as output.
Here,
    category is the starting point where the database to be classified,
    database is the name of the database,
    t_ec is the threshold value of coverage
    t_es is the threshold value of specificity
    expecificity_C is the value of the parent's specificity

To do the classification, we use the same algorithm as described in Figure 4 of the QProber paper. Which classify the database by calculating the coverage and the specificity up-down. And go down the category tree only if it reach the threshold.
We implement the algorithm recursively, and meanwhile add the sample URLs recursively.

        for child in category.children:
            if especificity[child.label] >= t_es and ecoverage[child.label] >= t_ec:
                tmp_result = classify(child, database, t_ec, t_es, especificity[child.label])
                result.extend(tmp_result[0])
                path = path + '/' + tmp_result[1]
                add_urls(category.label, database, document_samples[(child.label, database)])


Part 2 Topic content summary

When querying the database(in the function "classify"), we have already recursively stored the urls under each category into the dictionary called document_samples, which use (category, database) as key and store all the top4 urls related.

For each category under which we classified a given database, we use Lynx to retrieve term in the document and calculate the frequency in the document sample. Then write the result to txt file.
Here we neglected the retrieval of "PDF", "PPT", "PPTx" file since we find out the retrieval result for these file is not relevant to the file itself, but more likely some mistakenly parsed words by Lynx.


----------------
e. Bing Account Key

"OFzQIRuHcxWsxd0/QCQeUSvDsQOW/mVkEJygRt2rnUE"