# Semantic Scaling: Linguistic Substitution to show relationships rather than 2d mindmap
1. The idea is that mindmaps can show more information at once than can be represented in prose. However, what if we had a system for zooming in and out of a text that did not result in changing the size of displayed text but rather to show the structure within which it is nested (zoom out) and the elements nested within it (zoom in).
2. Ai can already be used to expand or shrink a text.
3. **Inquiry-Based Document Generation:** Text that can expand and contract provides a static view of each step of the user's dynamic exploration of a topic in a way that can be related to the original state of the text. This feature can be used to translate exploration/browsing into a draft document.
4. **Modularity:** In the original StretchText, a word can be substituted by another pre-written text that adds more detail to the passage. However, this approach seems barely modular. Our solution breaks down each concept to the point where expansion and contraction can be done at any point of any text without creating logical contradictions.
5. **Maximum Size:** There should be a maximum size for a section. Otherwise, you could theoretically expand a single paragraph to display all the information contained on the internet. Therefore, once a block reaches its maximum size, a new block should be created, somehow related to the text around its pointer in the previous block. Ideally, the program creates a new block before the previous one reached its maximum size.

**Related**
1. [[StretchText by Ted Nelson]]
2. [[Stretch Text]]

