# Tests 

Tests have been implemented to ensure the correctness of PanGBank-cli. 


## Unit tests 

Unit tests have been implmented in the tests directory using pytest. 


To run the test suit you would need to  have install PanGBank-cli from the source code.  For that, you can follow installation instructions [here](./installation.md#from-the-source-code-within-a-conda-environnement).


To install pytest in you environement you can run :

```bash
pip install .[dev]
```

Next, you can simply run the following at the root of the directory:

```bash
pytest  
```

To get the percentage of coverage of the test suit can be obtain as follow:

```bash
pytest --cov=pangbank 
```


<!-- ```{note}

Test coverage is updated by a github workflow in the Action Tab. The test coverage report is then deployed on the github-pages and avalaible [here](<link>). 

``` -->


<!-- ## Functional Tests -->
