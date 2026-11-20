# Final locked-test evaluation

Deployment fixed BEFORE test: LR tuned C=2. No selection from test.

candidate,split,accuracy,classes_f1_zero,macro_f1,macro_precision,macro_recall,predicted_classes,weighted_f1
lr_baseline,validation,0.8370910384068279,28,0.7878081402467481,0.8274197939731976,0.7791885208694249,560,0.836675385063782
lr_baseline,test,0.8426922254685384,28,0.7958306745796887,0.8304710522444024,0.7878866151893594,560,0.8428343938933989
lr_tuned_c2,validation,0.8376600284495022,23,0.7931543818638241,0.8238666389449272,0.7924848742690451,566,0.838439717113135
lr_tuned_c2,test,0.8440818071688163,22,0.808163486172862,0.8370725901054068,0.8047515247665102,567,0.8449466206008978
hard_tuned_lr_svc_knn,validation,0.8369132290184922,21,0.7965170720239344,0.8227126480439321,0.7981336562721902,567,0.8376817578041393
hard_tuned_lr_svc_knn,test,0.842834746668567,22,0.8059813671672197,0.8332232904614251,0.8046199889724036,567,0.84360287513484

Paired transitions (candidate vs reference):
reference,candidate,both_correct,both_wrong,rescues,new_errors,equal_group_accuracy_reference,equal_group_accuracy_candidate,equal_group_delta,groups_improved,groups_worsened,groups_equal
lr_baseline,lr_tuned_c2,23534,4259,156,117,0.9057887899667986,0.907450551588565,0.0016617616217663974,100,61,24967
lr_tuned_c2,hard_tuned_lr_svc_knn,23499,4220,156,191,0.907450551588565,0.9064231452423908,-0.0010274063461742542,71,106,24951
lr_baseline,hard_tuned_lr_svc_knn,23398,4158,257,253,0.9057887899667986,0.9064231452423908,0.0006343552755921426,146,142,24840

Equal-group differences are descriptive, not significance tests. Synthetic dataset; conflicting labels may share symptom vectors. Phase1 inspected the whole raw CSV. Held out from fitting/tuning, not a pristine blind external test. No clinical validation, calibrated probabilities or measured LLM-input generalization. Deployment remains LR tuned C=2 regardless of scores.
