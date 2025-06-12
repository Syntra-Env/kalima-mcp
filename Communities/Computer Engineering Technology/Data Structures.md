0. ## Data Structures: data organization in computer memory for efficient processing
1. Sequential files
2. polymorphism: same structures with different behavior
3. inheritance
4. encapsulation
5. ## Big O notation
   1. best-case
   2. average-case
   3. worst-case
   4. degree of a polynomial
6. ## recursion
   1. recursion uses a selection statement whereas iteraction uses an iteration statement.
   2. base case
   3. recursion step / recursive call: includes a return statement 
   4. induction also has a base case and induction step. How does it differ from recursion?
   5. termination test
   6. producing smaller versions of the original problem
   7. use recursion if if makes program easier to understand and debug
   8. recursion often requires less lines of code
7. ## searching algorithms
   1.  binary search
   2.  linear search
8. ## sorting algorithms
    1.  bubble sort
    2.  insertion sort
    3.  selection sort
    4.  quick sort
    5.  merge sort
9.  optimization
10. method tracing
11. generics
12. java collections framework (JCF)
13. collection class
14. Linked list
15. native 
16. singly linked lists
17. doubly linked lists
18. collection class
19. LL collection class
20. complex nested loops
21. binary search trees
22. tree traversal algorithms
    1.  treeset
    2.  treemap
23. sets
24. maps: key-value mapping
25. in-order
26. pre-order
27. post-order
28. hash table
29. hashing
30. Heap
    1. FIFO (?)
    2. Max Heap
    3. Min Heap
31. Stack: LIFO
    1.  stack frame
32. queues: FIFO
33. priority queues
34. efficiency
35. Data structures [0] are not stored in memory, they are only created when the program starts running to enable efficient processing
36. ## multidimensional arrays
    1.  the outer loop for a 2D array iterates over the rows
    2.  the inner loop for a 2D array iterates over the columns
37. # Sorting Algorithms
38. in-place sort
39. divide and conquer: 
    1.  makes sub-arrays
    2.  works better/organically with recursion
40. ## Bubble Sort
41. inner loop: largest item to the end of the array
42. outer loop: compare and exchange adjacent items using tempVar
43. two nested loops: O(n^2)
44. can be used with small amount of data for its simplicity
45. for i, find smallest element and swap it with element at i
46. ## Selection Sort
    1.  select the smallest element
    2.  swap smallest element with element at position i
    3.  i++
47. ## Insertion Sort
    1.  split array in sorted and unsorted
    2.  compare first unsorted element with all elements in the sorted section
    3.  place the firs unsorted element in a temporary variable.
    4.  for (i=1; i < array.length; ++i)
    5.  j=i-1
48. ## Quick Sort
49. pivot choice: first element or media point or last element (james's favorite :P)
50. [i] <pivot> [j]
51. i is looking for smaller elements
52. j is looking for bigger elements
53. ## Big O Notation
54. search algorithms
55. recursion
56. linear search
57. binary search
58. program efficiency analysis
59. algorithmic efficiency factors
60. CPU (time) usage
61. time complexity
62. functions for analyzing algorithms

| notation      | name            |
| ------------- | --------------- |
| O(1)          | constant        |
| O(log(n))     | logarithmic     |
| O((log(n))^c) | polylogarithmic |
| O(n)          | linear          |
| O(n^2)        | quadratic       |
| O(n^c)        | polynomial      |
| O(c^n)        | exponential     |

- Index-based algorithms have a constant time
- linear scales with increase of data proportionally
- ? do n-dimensional arrays require n-nested loops to parse every element?

```java
for (i<n) { // time complexity: n*m
    for (i<m) {
 }
}
```

- ordered arrays
- unordered arrays
- searching
- insertion
- deletion
- ? When is using an ordered array more efficient for searching, insertion and deletion?
- range: how data/how many elements must be searched
- logarithms: raising 2 to a poower is the inverse of a logarithm
- Log a (b) = c : which power (c) is a number (a) raised to in order to result in a number (b)?
- Binary search: compare search key with mid-point value
- asympototic behavior of polynomiall function: as the data approaches infinity, how many steps are required?
- the power of the range expressed in powers of 2 is equivalent to the number of steps required to search using binary search
- 2^n = 64 -> log 2 (64) "log of 64 to base 2"
- converting log base 2 to log base 10
- big O notation only consideres the worst case scenario


| Data Structure | Access | Insert at front | Insert at end |
| -------------- | ------ | --------------- | ------------- |
|                |        |                 |               |