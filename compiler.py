import re

f = open("main.drum", "r")
code = f.readlines()

asm = [
    "push ebp",
    "mov ebp, esp",
]

asm_queue = []

data = ["\nBASE_REG1 dd 0 \nBASE_REG2 dd 0 \nBASE_REG3 dd 0"]
adopted_filename = ""
functions = []
function_stack = [None]
arrays = []
append_without_parsing = False
macros = [
    "%macro write_string 2 ",
        "mov eax, 4",
        "mov ebx, 1",
        "mov ecx, %1",
        "mov edx, %2",
        "int 80h",
    "%endmacro",    
]

def get_function_index_from_name(function_name):
    for i, x in enumerate(functions):
        if x[0] == function_name:
            return(i)
        
def create_function_if_nonexistent(function_name):
    exists = False
    for x in functions:
        if x[0] == function_name:
            exists = True
    
    if not exists:
        functions.append([function_name, []])

def asm_append(line, ignore_stack=False, stack_offset=0):
    func = function_stack[0+stack_offset]
    if func == None or ignore_stack:
        asm.append(line)
    elif func != None:
        functions[get_function_index_from_name(func)][1].append(line)

#Also poorly named
def parse_array_operation(line, array_name, close_index, append=False):
    multiplier = 4
    array = get_array_entry(array_name)
    index = get_variable_name(line[close_index:], enclose=True)
    start_index = array[2]
    if append:
        asm_append("mov edx, " + index)
        asm_append("add edx, " + str(start_index))
    return("[esp + " + str(multiplier) + " * edx]")
    
def get_array_entry(array_name):
    for x in arrays:
        if x[0] == array_name:
            return x

def is_variable_array(variable_name):
    for x in arrays:
        if x[0] == variable_name:
            return True
    return False

#Poorly named, might fix one day.
#Should probably make variable_name.group(1) a var for readability
def get_variable_name(line, enclose=False, allownone=False, append_if_array_operation=False):
    original_line = line
    
    i = 0
    if line.count("$") > 2:
        for j, x in enumerate(line):
            if x == "$": i += 1
            if i == 2: 
                line = line[:-j-1].strip()
                i = j + 2
                break
    else:
        i = line.rfind("$") + 2
            
    variable_name = re.search(r'.*?\$(.*)\$.*' , line)
    if variable_name: 
        if is_variable_array(variable_name.group(1)):
            return(parse_array_operation(original_line, variable_name.group(1), i, append=append_if_array_operation))
        if enclose:
            return("[" + variable_name.group(1) + "]")
        else:
            return(variable_name.group(1))
        
    if allownone:
        return None
    return line

def if_statement(line, index):
    line = line.strip()
    instruction = None
    instructions = {
        "==": "je",
        ">": "jg",
        "<": "jl",
        ">=": "jge",
        "<=": "jle",
        "!=": "jne"
    }
    
    args = re.split('>|<|==|>=|<=|!=|\n', line[3:])
    
    function_name = adopted_filename + "_" + "if_" + str(index)
    for i, x in enumerate(args):
        args[i] = args[i].replace('=', '').strip()
        args[i] = get_variable_name(args[i], enclose=True)
        if args[i] == "": args.pop(i)
    
    for x in instructions:
        if x in line: instruction = instructions[x]
    
    asm_append("mov eax, " + str(args[1]))
    asm_append("cmp " + str(args[0]) + ", eax")
    asm_append(instruction + " " + function_name)
    
    function_stack.insert(0, function_name)
    create_function_if_nonexistent(function_name)
    asm_append(function_name + "_return:", stack_offset=1)

def function_declaration(line):
    function_name = "FUNC_" + line.split()[1]
    function_stack.insert(0, function_name)
    create_function_if_nonexistent(function_name)
    
def variable_operation(line):
    line = line.replace(" ", "")
    operation = None
    operations = ["+", "-", "*", "/", "="]
    a = b = None
    for x in operations:
        if x in line:
            operation = x
            line_split = line.split(operation)
            a = get_variable_name(line_split[0], enclose=True, append_if_array_operation=True).strip()
            b = get_variable_name(line_split[1], enclose=True, append_if_array_operation=True).strip()
            break
    
    asm_append("mov eax, " + b) 
    if operation == "+":
        asm_append("add " + a + ", eax")
    if operation == "-":
        asm_append("sub " + a + ", eax")
    if operation == "=":
        asm_append("mov " + a + ", eax")
    
def end_statement():
    function_stack.pop(0)

def print_statement(line):
    variable_name = get_variable_name(line)
    asm_append("write_string " + variable_name + ", " + variable_name + "len")

def goto_statement(line):
    asm_append(line.replace("goto", "jmp").strip())    
    
def call_statement(line):
    line_split = line.split()
    function_name = line_split[1].replace(",", "").strip()
    function_args = line.split(",")
    
    if len(function_args) > 1:
        asm_append("mov eax, " + get_variable_name(function_args[1].replace(",", "").strip(), enclose=True))
        asm_append("mov [BASE_REG1], eax")
    if len(function_args) > 2:
        asm_append("mov eax, " + get_variable_name(function_args[2].replace(",", "").strip(), enclose=True))
        asm_append("mov [BASE_REG2], eax")
    if len(function_args) > 3:
        asm_append("mov eax, " + get_variable_name(function_args[3].replace(",", "").strip(), enclose=True))
        asm_append("mov [BASE_REG3], eax")
    
    if function_stack[0]:
        asm_append("jmp"+ " FUNC_" + function_name) 
    else:
        asm_append(line_split[0] + " FUNC_" + function_name)   

def adopt_declaration(line):
    global adopted_filename
    f = open(line.split()[1].strip(), "r")
    code = f.readlines()
    adopted_filename = line.split()[1].replace(".drum", "")
    parse_lines(code)
    adopted_filename = ""
        
def string_declaration(line):
    string_name = line.split()[1]
    string_value = line[line.index("=")+1:].lstrip().rstrip('\n')
    data.append("\n" + string_name + " db \"" + string_value + "\"")
    data.append("\n" + string_name + "len equ $ - " + string_name)

def numeral_declaration(line):
    numeral_name = line.split()[1]
    numeral_value = line[line.index("=")+1:].lstrip().rstrip('\n')
    data.append("\n" + numeral_name + " dd " + numeral_value + "")

def label_declaration(line):
    asm_append(line.split()[1] + ":")

def array_declaration(line):
    array_name = line.split()[1].strip()
    array_length = line.split("=")[1].strip()
    if(arrays == []):
        arrays.append((array_name, int(array_length), 1))
    else:
        arrays.append((array_name, int(array_length), (arrays[-1][1] + arrays[-1][2]) + 1))
    
def parse_lines(lines):
    global append_without_parsing
    for i, line in enumerate(lines):
        line_split = line.split()
        if(line_split):
            keyword = line_split[0]
        else: keyword = "N/A"
        
        if(asm_queue != []):
            asm_append(asm_queue[0])
            asm_queue.pop(0)
            
        if not append_without_parsing:
            if keyword == "string":
                string_declaration(line)         
            if keyword == "numeral":
                numeral_declaration(line)  
            if keyword == "print":
                print_statement(line)          
            if keyword == "label":
                label_declaration(line)
            if keyword == "goto":
                goto_statement(line)
            if keyword == "if":
                if_statement(line, i)
            if keyword == "function":
                function_declaration(line)
            if keyword == "call":
                call_statement(line)
            if keyword == "end":
                end_statement()
            if keyword == "adopt":
                adopt_declaration(line)
            if keyword == "array":
                array_declaration(line)
            if keyword == "<asm":
                append_without_parsing = True
            if get_variable_name(keyword, allownone=True):
                variable_operation(line)
        else:
            if line.strip() == "asm>":
                append_without_parsing = False
            else:
                asm_append(line.strip())

def compile():
    parse_lines(code)
    result = ""
    #Add macros
    for x in macros:
        result += "\n" + x
        
    #Add functions
    for x in functions:
        if x[0][0] != "%":
            result += "\n\n" + x[0] + ":"
            for y in x[1]:
                result += "\n" + y
            if("FUNC_" not in x[0]):
                result += "\njmp " + x[0] + "_return"
            else:
                result += "\nret"
        else:
            result += "\n\n" + x[0]
            for y in x[1]:
                result += "\n" + y
            result += "\n%endmacro"
        
    result += "\n\nglobal _start\n_start:"
    for x in asm:
        result += "\n" + x 
    result += "\nmov eax, 1\nint 0x80"
    
    #Build data section
    result += "\nsection .data"
    for x in data:
        result += x
    return result
           
print(compile())
