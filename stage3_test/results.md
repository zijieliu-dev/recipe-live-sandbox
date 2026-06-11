# Stage 3 — full results (200 recipes, fired with no crafted input)

| # | recipe | connector | result | live ops / reason |
|--|--------|-----------|--------|-------------------|
| 1 | 126224282 | jira | ❌ error | step #2 jira::search_issues: dispatch raised  |
| 2 | 131740928 | jira | ❌ error | step #2 jira::create_comment: dispatch raised |
| 3 | 123601352 | jira | ❌ error | step #2 jira_service_desk::create_comment: di |
| 4 | 97678913 | jira | ❌ error | step #3 jira::update_issue: dispatch raised U |
| 5 | 63784713 | jira | ❌ error | step #2 jira::search_issues_by_JQL: dispatch  |
| 6 | 131689462 | jira | ❌ error | step #2 jira::get_issue: dispatch raised URLE |
| 7 | 117982777 | jira | ❌ error | step #2 jira::find_user: dispatch raised URLE |
| 8 | 107394462 | jira | ❌ error | step #2 jira::get_issue: dispatch raised URLE |
| 9 | 124193123 | jira | ❌ error | step #2 jira::get_issue: dispatch raised URLE |
| 10 | 131479284 | jira | ❌ error | step #2 jira::find_user: dispatch raised URLE |
| 11 | 119545129 | jira | ❌ error | step #2 jira::get_issue: dispatch raised URLE |
| 12 | 124712808 | jira | ❌ error | step #2 jira::create_issue: dispatch raised U |
| 13 | 129676100 | jira | ❌ error | step #2 jira_service_desk::create_customer_re |
| 14 | 131719724 | jira | ❌ error | step #2 jira::create_issue: dispatch raised U |
| 15 | 129761794 | jira | ❌ error | step #4 jira::create_issue: dispatch raised U |
| 16 | 117164680 | jira | ⚪ ran (no write) | slack_bot::delete_message(no-effect) |
| 17 | 123396581 | jira | ⚪ ran (no write) |  |
| 18 | 123871665 | jira | ⚪ ran (no write) |  |
| 19 | 123872506 | jira | ⚪ ran (no write) |  |
| 20 | 115644381 | jira | ⚪ ran (no write) |  |
| 21 | 126124642 | jira | ⚪ ran (no write) |  |
| 22 | 123872501 | jira | ⚪ ran (no write) |  |
| 23 | 126126639 | jira | ⚪ ran (no write) |  |
| 24 | 109835280 | jira | ⚪ ran (no write) |  |
| 25 | 112589461 | jira | ⚪ ran (no write) | slack_bot::delete_message(no-effect) |
| 26 | 126126645 | jira | ⚪ ran (no write) |  |
| 27 | 89204644 | jira | ⚪ ran (no write) |  |
| 28 | 126126641 | jira | ⚪ ran (no write) |  |
| 29 | 130740417 | jira | ⚪ ran (no write) |  |
| 30 | 126124540 | jira | ⚪ ran (no write) |  |
| 31 | 130612377 | jira | ⚪ ran (no write) |  |
| 32 | 126124505 | jira | ⚪ ran (no write) |  |
| 33 | 123871640 | jira | ⚪ ran (no write) |  |
| 34 | 126126648 | jira | ⚪ ran (no write) |  |
| 35 | 131351266 | jira | ⚪ ran (no write) |  |
| 36 | 126124460 | jira | ⚪ ran (no write) |  |
| 37 | 107045201 | jira | ⚪ ran (no write) |  |
| 38 | 131285758 | jira | ⚪ ran (no write) |  |
| 39 | 117993644 | jira | ⚪ ran (no write) | slack_bot::delete_message(no-effect) |
| 40 | 126126650 | jira | ⚪ ran (no write) |  |
| 41 | 123872509 | jira | ⚪ ran (no write) |  |
| 42 | 126224293 | jira | ⚪ ran (no write) |  |
| 43 | 119548071 | jira | ⚪ ran (no write) |  |
| 44 | 123872498 | jira | ⚪ ran (no write) |  |
| 45 | 126126647 | jira | ⚪ ran (no write) |  |
| 46 | 123872508 | jira | ⚪ ran (no write) |  |
| 47 | 126126651 | jira | ⚪ ran (no write) |  |
| 48 | 112590005 | jira | ⚪ ran (no write) |  |
| 49 | 126126643 | jira | ⚪ ran (no write) |  |
| 50 | 126124574 | jira | ⚪ ran (no write) |  |
| 51 | 131491130 | slack | ❌ error | 400 |
| 52 | 95449201 | slack | ❌ error | 400 |
| 53 | 119464616 | slack | ❌ error | 404 |
| 54 | 120099657 | slack | ✅ live-write | slack_bot::post_bot_reply_v2 · slack_bot::post_bot_message |
| 55 | 122118451 | slack | ✅ live-write | slack_bot::post_bot_message |
| 56 | 106839710 | slack | ✅ live-write | slack_bot::post_bot_message · slack_bot::post_bot_message |
| 57 | 119494368 | slack | ✅ live-write | slack_bot::block_kit_modals(no-effect) · slack_bot::block_kit_modals(no-effect)  |
| 58 | 122219101 | slack | ✅ live-write | slack_bot::block_kit_modals(no-effect) · slack_bot::post_bot_message |
| 59 | 88778869 | slack | ✅ live-write | slack_bot::post_bot_reply_v2 |
| 60 | 89648185 | slack | ✅ live-write | slack_bot::post_bot_message |
| 61 | 88676319 | slack | ✅ live-write | slack_bot::post_bot_message |
| 62 | 115842976 | slack | ✅ live-write | slack_bot::post_bot_message · slack_bot::block_kit_modals(no-effect) · salesforc |
| 63 | 91361540 | slack | ✅ live-write | slack_bot::post_bot_message |
| 64 | 128966631 | slack | ⚪ ran (no write) |  |
| 65 | 87839087 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 66 | 116627177 | slack | ⚪ ran (no write) |  |
| 67 | 103800161 | slack | ⚪ ran (no write) | slack_bot::delete_message(no-effect) |
| 68 | 130297281 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 69 | 120637746 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 70 | 130297160 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 71 | 84503701 | slack | ⚪ ran (no write) |  |
| 72 | 86470328 | slack | ⚪ ran (no write) |  |
| 73 | 57440134 | slack | ⚪ ran (no write) |  |
| 74 | 100175840 | slack | ⚪ ran (no write) | slack_bot::delete_message(no-effect) |
| 75 | 125804198 | slack | ⚪ ran (no write) |  |
| 76 | 88676445 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 77 | 102360789 | slack | ⚪ ran (no write) |  |
| 78 | 87410086 | slack | ⚪ ran (no write) |  |
| 79 | 92726378 | slack | ⚪ ran (no write) |  |
| 80 | 100313677 | slack | ⚪ ran (no write) | slack_bot::delete_message(no-effect) |
| 81 | 129057542 | slack | ⚪ ran (no write) |  |
| 82 | 100458488 | slack | ⚪ ran (no write) |  |
| 83 | 87835181 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 84 | 57590684 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 85 | 115440327 | slack | ⚪ ran (no write) |  |
| 86 | 57440067 | slack | ⚪ ran (no write) |  |
| 87 | 114726176 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 88 | 88676796 | slack | ⚪ ran (no write) |  |
| 89 | 108424002 | slack | ⚪ ran (no write) |  |
| 90 | 121627662 | slack | ⚪ ran (no write) |  |
| 91 | 108425186 | slack | ⚪ ran (no write) |  |
| 92 | 120268359 | slack | ⚪ ran (no write) |  |
| 93 | 50816343 | slack | ⚪ ran (no write) |  |
| 94 | 118521989 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 95 | 95282141 | slack | ⚪ ran (no write) |  |
| 96 | 94270840 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 97 | 94382824 | slack | ⚪ ran (no write) |  |
| 98 | 116478121 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 99 | 86905118 | slack | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 100 | 107355143 | slack | ⚪ ran (no write) |  |
| 101 | 100259468 | sheets | 💥 crash | Expecting value: line 1 column 1 (char 0) |
| 102 | 94196410 | sheets | ❌ error | step #4 jira::get_issue: dispatch raised URLE |
| 103 | 112579016 | sheets | ✅ live-write | slack_bot::block_kit_modals(no-effect) · slack_bot::post_bot_message |
| 104 | 112565699 | sheets | ✅ live-write | slack_bot::block_kit_modals(no-effect) · slack_bot::post_bot_message |
| 105 | 125787861 | sheets | ✅ live-write | google_sheets::add_row_v4_bulk |
| 106 | 50816137 | sheets | ✅ live-write | google_sheets::add_row_v4_bulk |
| 107 | 123992155 | sheets | ✅ live-write | slack_bot::post_bot_message |
| 108 | 118639009 | sheets | ✅ live-write | slack_bot::block_kit_modals(no-effect) · slack_bot::post_bot_message · slack_bot |
| 109 | 114287788 | sheets | ✅ live-write | google_sheets::add_row_v4_bulk · slack::post_message_to_channel |
| 110 | 118716983 | sheets | ✅ live-write | slack_bot::post_bot_message · slack_bot::post_bot_message · slack_bot::post_bot_ |
| 111 | 88782312 | sheets | ✅ live-write | slack_bot::post_bot_message |
| 112 | 121887522 | sheets | ✅ live-write | slack_bot::post_bot_message · slack_bot::post_bot_message |
| 113 | 117976116 | sheets | ✅ live-write | slack_bot::post_bot_reply_v2 |
| 114 | 118858472 | sheets | ✅ live-write | slack_bot::post_bot_message · slack_bot::post_bot_message |
| 115 | 123424618 | sheets | ✅ live-write | slack_bot::post_bot_message |
| 116 | 91495261 | sheets | ⚪ ran (no write) |  |
| 117 | 107958218 | sheets | ⚪ ran (no write) |  |
| 118 | 113372255 | sheets | ⚪ ran (no write) |  |
| 119 | 97310798 | sheets | ⚪ ran (no write) |  |
| 120 | 87241695 | sheets | ⚪ ran (no write) | slack_bot::post_bot_message(no-effect) · slack_bot::post_bot_message(no-effect) |
| 121 | 88932216 | sheets | ⚪ ran (no write) | slack_bot::block_kit_modals(no-effect) |
| 122 | 101566146 | sheets | ⚪ ran (no write) |  |
| 123 | 122667286 | sheets | ⚪ ran (no write) |  |
| 124 | 97310526 | sheets | ⚪ ran (no write) |  |
| 125 | 100084246 | sheets | ⚪ ran (no write) |  |
| 126 | 100084088 | sheets | ⚪ ran (no write) |  |
| 127 | 124796779 | sheets | ⚪ ran (no write) |  |
| 128 | 23260621 | sheets | ⚪ ran (no write) |  |
| 129 | 129533209 | sheets | ⚪ ran (no write) |  |
| 130 | 118162510 | sheets | ⚪ ran (no write) |  |
| 131 | 97310593 | sheets | ⚪ ran (no write) |  |
| 132 | 122043257 | sheets | ⚪ ran (no write) |  |
| 133 | 97310564 | sheets | ⚪ ran (no write) |  |
| 134 | 97310724 | sheets | ⚪ ran (no write) |  |
| 135 | 108510475 | sheets | ⚪ ran (no write) |  |
| 136 | 97310457 | sheets | ⚪ ran (no write) |  |
| 137 | 97310640 | sheets | ⚪ ran (no write) |  |
| 138 | 87241419 | sheets | ⚪ ran (no write) |  |
| 139 | 97310663 | sheets | ⚪ ran (no write) |  |
| 140 | 95543180 | sheets | ⚪ ran (no write) |  |
| 141 | 115133064 | sheets | ⚪ ran (no write) |  |
| 142 | 122080535 | sheets | ⚪ ran (no write) |  |
| 143 | 97310532 | sheets | ⚪ ran (no write) |  |
| 144 | 106355886 | sheets | ⚪ ran (no write) |  |
| 145 | 130998008 | sheets | ⚪ ran (no write) |  |
| 146 | 122663844 | sheets | ⚪ ran (no write) |  |
| 147 | 130844792 | sheets | ⚪ ran (no write) |  |
| 148 | 129408136 | sheets | ⚪ ran (no write) |  |
| 149 | 113744754 | sheets | ⚪ ran (no write) |  |
| 150 | 121973481 | sheets | ⚪ ran (no write) |  |
| 151 | 131003690 | sf | ❌ error | 400 |
| 152 | 115850922 | sf | ❌ error | 400 |
| 153 | 116477352 | sf | ❌ error | 400 |
| 154 | 85944334 | sf | ❌ error | 400 |
| 155 | 91447602 | sf | ❌ error | 400 |
| 156 | 100083995 | sf | ❌ error | 400 |
| 157 | 123613324 | sf | ❌ error | step #2 salesforce::upsert_sobject: dispatch  |
| 158 | 129023208 | sf | ❌ error | 404 |
| 159 | 53837831 | sf | ❌ error | 400 |
| 160 | 118269695 | sf | ❌ error | 400 |
| 161 | 125405385 | sf | ❌ error | 400 |
| 162 | 129809029 | sf | ❌ error | 400 |
| 163 | 103939956 | sf | ❌ error | 400 |
| 164 | 95315726 | sf | ❌ error | 400 |
| 165 | 128375319 | sf | ❌ error | 400 |
| 166 | 131596457 | sf | ❌ error | 400 |
| 167 | 129944080 | sf | ✅ live-write | salesforce::composite_update_sobject · salesforce::composite_update_sobject |
| 168 | 123612780 | sf | ✅ live-write | salesforce::update_sobject |
| 169 | 130632724 | sf | ✅ live-write | salesforce::create_custom_object |
| 170 | 129868323 | sf | ✅ live-write | salesforce::composite_update_sobject · salesforce::composite_update_sobject |
| 171 | 123586631 | sf | ✅ live-write | salesforce::__adhoc_http_action |
| 172 | 127792368 | sf | ✅ live-write | salesforce::composite_update_sobject · salesforce::composite_update_sobject |
| 173 | 123520875 | sf | ✅ live-write | salesforce::update_sobject |
| 174 | 129491110 | sf | ✅ live-write | salesforce::update_sobject |
| 175 | 130598511 | sf | ✅ live-write | salesforce::composite_create_sobject |
| 176 | 123464993 | sf | ✅ live-write | salesforce::create_custom_object |
| 177 | 129494069 | sf | ✅ live-write | salesforce::update_sobject |
| 178 | 110860843 | sf | ⚪ ran (no write) |  |
| 179 | 87147147 | sf | ⚪ ran (no write) |  |
| 180 | 85363714 | sf | ⚪ ran (no write) |  |
| 181 | 85934045 | sf | ⚪ ran (no write) |  |
| 182 | 121558132 | sf | ⚪ ran (no write) |  |
| 183 | 85191811 | sf | ⚪ ran (no write) |  |
| 184 | 85363715 | sf | ⚪ ran (no write) |  |
| 185 | 117385106 | sf | ⚪ ran (no write) |  |
| 186 | 87147151 | sf | ⚪ ran (no write) |  |
| 187 | 86115054 | sf | ⚪ ran (no write) |  |
| 188 | 84791377 | sf | ⚪ ran (no write) |  |
| 189 | 110860092 | sf | ⚪ ran (no write) |  |
| 190 | 85191812 | sf | ⚪ ran (no write) |  |
| 191 | 128228340 | sf | ⚪ ran (no write) |  |
| 192 | 127926565 | sf | ⚪ ran (no write) |  |
| 193 | 85359618 | sf | ⚪ ran (no write) |  |
| 194 | 129809028 | sf | ⚪ ran (no write) |  |
| 195 | 110860328 | sf | ⚪ ran (no write) |  |
| 196 | 91244712 | sf | ⚪ ran (no write) |  |
| 197 | 84963065 | sf | ⚪ ran (no write) |  |
| 198 | 86114917 | sf | ⚪ ran (no write) |  |
| 199 | 123622274 | sf | ⚪ ran (no write) |  |
| 200 | 126881041 | sf | ⚪ ran (no write) |  |
