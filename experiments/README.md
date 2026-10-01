# Experiments for: "Identifying GDPR-Critical Tasks in Business Processes Using Large Language Models"
This folder contains all data for the experiments conducted to evaluate the LLM component in GRIPL.  

#### Configurations

under \configurations, you can find the .yaml configs for all evaluation runs completed with the GRIPL evaluation framework. Configurations are aggregated by LLM families (deepseek, openai, google and mistral).

A configuration is made up of the following parameters:

```yaml
defaultEvaluationEndpoint: <Endpoint url, e.g. /gdpr/analysis/prompt-engineering>
seed: <a reproducible seed>
maxConcurrent: 10
repetitions: 5 
models:
  - label: <Model name: e.g DeepSeek-V3.1>
    llmProps:
      baseUrl: https://openrouter.ai/api/v1
      modelName: <open router model name, e.g. deepseek/deepseek-chat-v3.1>
      apiKey: ${OPEN_ROUTER_API_KEY}
      temperature: 0.1
      topP: 1
datasets: <list of dataset IDs>
```



#### Prompts

This folder collects all prompts used for the experiment. As in this experiment the zero-shot capabilities of LLMs were tested, there is only one system prompt (GRIPL_baseline_prompt.md)



#### Dataset

under \dataset you can find the dataset consisting of 93 BPMN models. 

- \Raw BPMN, contains all 93 raw BPMN models (82 exported from Signavio, 11 created with other BPMN tools)

- \Annotated Dataset contains the datasets grouped by domain (dataset.csv) and all 93 labeled BPMN models (evaluation_data.csv) - these can be imported into the postgres DB for GRIPL

  - annotations.xlsx includes the labels of all 940 activities from the different annotators (n=3)

- \utils contains helper scripts for data analysis and labeling

  

#### Results

This folder contains all the raw result data exported from GRIPL (GRIPL Results Export) along with all aggregated analyses presented in the paper (Analysis).


#### Changelog

v1.1
- labeled_activities.xlsx replaced by annotations.xlsx: the previous file contained labels from a faulty ID extraction (554 instead of 617 critical activities) and annotator columns copied from these labels.
- evaluation_data.csv replaced by the export used for the experiment runs (labels unchanged).
- Analysis: fixed critical-activity extraction, the Mistral-Medium-3.1 label in the RQ2 grouping and the RQ3 scoring of test cases without critical activities; outputs renamed by research question (rq2_…, rq3_…).