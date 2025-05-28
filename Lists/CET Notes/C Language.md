0. # C Language
1. strict procedural language
2. ## ANSI C standard
3. problem solving (debugging)
   1. "entering from multiple doors"
4. problem decomposition
   1. small testable components
   2. data-function coupling
5. # Architecture
6. is like a contract with developers
7. memory management
8.  parsing
9.  data structures (more in second half)
10. code/variable tracing
11. command line
12. parsing command line
13. makefiles
14. modular programming
15. scales of complexity
16. assembly language
17. processor
18. processor architecture
19. ## Comments
20. C comments = alt+shift+A = block comments = /* */
21. conventions
22. comments conventions
23. comment during the process of writing code
24. include comments to reference oonline code used
25. 1972 - Dennis Ritchie
26. Multix
27. Time sharing
28. ken thompson
29. libraries
30. statically linked library
31. dynamically linked / shared library
32. Unix
33. compiler
34. Link: combines object files, creates a single executable
35. Portability
36. portable compiler 
37. bitfields
38. binary operators
39. primitive types
40. [data structures] are systems of [primitive types]
41. arrays
42. control structures
43. memory address
44. 1988 [ansi standard]
45. ## Comparisons
46. bitwise comparisons
47. logical comparisons
48. [bitwise] vs [logical]
49. <=> is the spaceship operator
50. C has less guardrails than high-level languages
51. standards enable efficient collaboration
52. boilerplate
53. c.json boilerplate
54. /* filename.c
55.  * name
56.  * class/course
57.  * date
58.  * /
59. #include <stdio.h>
60. int main() { printf("hello world!"); return 0; }
61. gcc
    1.  gcc -ansi -pedantic -Wall -Wextra -o [executableFileName] [sourceCodeFilename].c
    2.  -E option: shows the code after the preprocessed defines are pasted everywhere they need to be in the code.
62. gdb
63. git
64. ./a.out
65. ## Pointer
    1.  pointer arithmetic
    2.  declarations at the top
    3.  always initialize variables
    4.  uninitialized variables cause to grab previously initialized values from heap
66. $?
67. ## Nonlocal Jumps <setjmp.h>
68. Macro: text replacement?
69. Buffer
70. calling environment
71. ## Common definitions <stddef.h>
72. integral type
73. signed & unsigned types
74. locales
75. digital certificates
76. Strongly typed
77. # Week 4
78. ## Print
    1.  - -> \0
    2.  '*'
    3.  '\n'
79. Procedure can only do one thing
    1.  separation of concerns
80. Preprocessor directives: don't take any memory???
    1.  #define
    2.  #include
81. if (argc != 3) error = 1;
82. namespaceL where names are reserved
    1.  memory location
    2.  offsets: from wherever you are in the stack currently
        1.  when we use an offset, we're gonna add that many to the side of the memory location
        2.  when it passes location in memory, does it pass the first location? is the offset then the side of that item in memory and used to determined the next freely available space in memory?
    3.  type: symbol table
    4.  bounds checking: if you go outside the array, you might get a segmentation error/fault (if you're lucky).
        1.  outside domain of OS, where it does not take care of memory allocation
    5.  string termination symbol: null: \0 -> "__" <- \0
83. What's the difference between the method prototype and method declaration?
84. method declaration: returnType functionName (type name pair(s)) {}
85. is the offest related to pointer arithmetic?
86. when you say it's good to initialize a variable because anything could be in it, do you mean it could be assigned a memory location that hasn't been freed before?
87. in which order are elements stored in the symbol item? does it have to do with how the program will be executed?
88. ## while vs for loop
89. for loop when you know when you want to loop to end
90. while loop when you don't know exactly when the loop will end or should end
91. while(string[i++] != '\0'); return i-1;
92. Union: single value, multiple types
93. Struct: multiple different values as a new type: takes care of the memory allocation for us: not necessarily contiguous in memory, could store its parts in different places in memory.
94. ## common input problems
95. snippet library: things you do over and over again:
96.  printf:
    1.  format specifiers (%%):
        1.  %12s, %7s, %6s
        2.  %[flags][width][precision][type_letter]
        3.  %d, %i (signed integer)
        4.  %u (unsigned integer) (gives us one more bit)
        5.  %f (real numbers)
        6.  %c (character)
        7.  %s (string)
        8.  %x (hex)
        9.  %o (octal)
97.  ### stream: 
    1.  input is parsing things that are coming to you on a stream
    2.  it is a path
    3.  examples
        1.  files
        2.  user input
        3.  http calls
    4.  handled by interrupts: pauses. stores environment and loads new environment then goes back to stored environment.
        1.  context switches: very costly, should be used sparsely
    5.  scanf: not useful since we can't trust users to follow the rules of the game
        1.  if there's nothing in the stream, it's going to stop and wait for an input
        2.  will take whatever was in the buffer/stream (like new line)
        3.  SOLUTION: flush the buffer when you'd like the stream to be reset and not include any previously unintentionally stored inputs in the stream. \n\r
    6.  &number = "give me address of 'number'" 
98.  Can use swtich case statement for fallthrough operations (if you don't want it to break after a case) that apply the same process for some inputs, with slight differences... sort of like method overloading
99.  ## Labels
100. thispart:
101. goto thispart; // jump routine
102. one instruction fits in one register/word/architecture bit size
103. Static Functions
     1.   available in the file in which they're defined
     2.   avoiding namespace collisions
104. # Week 5
105. indirection
106. pointers