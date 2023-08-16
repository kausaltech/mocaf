# Poll GraphQl

## Mutations

### Example mutation
```graphql
mutation @device(uuid: "4922d7d7-956f-40d0-803f-7d06a0c75d40", token: "500a6615-6ddf-4f79-a391-efcf89d33422") {
  pollEnrollToSurvey(surveyId: 8, backQuestionAnswers: "{\"x\":5,\"y\":6}", feelingQuestionAnswers: "{\"x\":5,\"y\":6}")  {
    ok
  }
}
```
### Example answer
```graphql
{
  "data": {
    "pollEnrollToSurvey": {
      "ok": true
    }
  }
}
```

### Enable/disable survey on machine.
enableSurvey

### Enable/disable survey on machine.
enableCarbon

### Add survey. Chk timeline.
pollAddSurvey

#### Arguments
days: Int!  //User survey days.
description: String = "" //Survey description.
endDay: Date! //Survey end day.
maxBackQuestion: Int //Amount of different survey questions, default 3.
startDay: Date! //Survey start day.

### Add user to survey. Select randomly survey days to user.
pollEnrollToSurvey

#### Arguments
backQuestionAnswers: String = "" //User answers to back question on JSON form.
feelingQuestionAnswers: String = "" //User answer to feeling questions on JSON form.
surveyId: ID //Id of question survey.

### Add trip to user. User trip times needs to be unigue. Returns trip Id.
pollAddTrip

#### Arguments
endMunicipality: String //Trip end municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu) Default Tampere.
endTime: DateTime! //Trip end time.
purpose: String //Trip purpose (tyo, opiskelu, tyoasia, vapaaaika, ostos, muu) Default empty.
startMunicipality: String //Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu) Default Tampere.
startTime: DateTime! //Trip start time.
surveyId: ID! //Survey Id.

### Add leg of the trip. Leg times need to be unigue. Trip needs to be unapproved.
pollAddLeg

#### Arguments
carbonFootprint: String = "" //Leg carbon footprint.
endLoc: PointScalar = "" //Leg end location.
endTime: DateTime! //Leg end time.
nrPassengers: String = "" //Amount of passengers.
startLoc: PointScalar = "" //Leg start location.
startTime: DateTime! //Leg start time.
transportMode: String = "" //Transport mode of the trip.
tripId: ID! //Trip Id.
tripLength: Float //Lengt of the trip.

### Update given information to trip. Trip times needs to be unique. Its not possible to approve unpurpose or empty trip.
pollEditTrip

#### Arguments
approved: Boolean //Approved (True/False).
endMunicipality: String = "" //Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu).
endTime: DateTime = "" //Trip end time.
purpose: String = "" //Trip purpose (tyo, opiskelu, tyoasia, vapaaaika, ostos, muu).
startMunicipality: String = "" //Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu).
startTime: DateTime = "" //Trip start time.
surveyId: ID! //Survey Id.
tripId: ID! //Trip Id.

### Mark user day ready. Chk that all day trip has purpose and leg.
pollMarkUserDayReady

#### Arguments
selectedDate: Date! //Selected day.
surveyId: ID! //Survey Id.

### Mark user survey ready. Chk that all day has been approved.
pollApproveUserSurvey

#### Arguments
surveyId: ID //surveyId: Survey Id.

### Register user to lottery.
pollEnrollLottery

#### Arguments
email: String! //Email.
name: String! //Name.

### Add empty question set in JSON form to database.
pollAddQuestion

#### Arguments
description: String! //Question Description.
question: String! //Question in JSON form.
questionType: String! //Question type (background, feeling, somethingelse).
surveyId: ID = "" //Question survey.

### Add locations to leg. Chk time of the leg.
pollLocationToLeg

#### Arguments
legId: ID! //Leg Id.
loc: PointScalar //Loc point.
time: DateTime = "" //Point time.

### Delete trip. Only unapproved trip can be deleted.
pollDelTrip

#### Arguments
surveyId: ID! //Survey Id.
tripId: ID! //Trip Id.

### Delete leg from the trip. Only leg from unapproved trip can be deleted.
pollDelLeg

#### Arguments
legId: ID! //Leg Id.
surveyId: ID! //Survey Id.
tripId: ID! //Trip Id.

### Compine two trip to one. Only unapproved trip can be compine.
pollJoinTrip

#### Arguments
surveyId: ID! //Survey Id.
trip2Id: ID! //Second trip Id.
tripId: ID! //First trip Id.

### Split one trip to two. Only unapproved trip can be split.
pollSplitTrip

#### Arguments
afterLegId: ID! //Last leg of first trip.
surveyId: ID! //Survey Id.
tripId: ID! //Trip Id.

### Saves user answers to question.
pollAddUserAnswerToQuestions

#### Arguments
backQuestionAnswers: String = "" //User answers to back question on JSON form.
feelingQuestionAnswers: String = "" //User answer to feeling questions on JSON form.
surveyId: ID! //Survey Id.

## Querys

### Example query
```graphql
query @device(uuid: "4922d7d7-956f-40d0-803f-7d06a0c75d40", token: "469443b1-6929-49bb-87c9-3aafea7b83f5"){
	pollSurveyInfo  {
    		startDay
    		endDay
    		days
    		maxBackQuestion
    		description
  }
}
```
### Example answer
```graphql
{
  "data": {
    "pollSurveyInfo": [
      {
        "startDay": "2023-08-14",
        "endDay": "2023-08-16",
        "days": 3,
        "maxBackQuestion": 3,
        "description": "kokeilu"
      },
      {
        "startDay": "2023-07-04",
        "endDay": "2023-07-07",
        "days": 3,
        "maxBackQuestion": 3,
        "description": "kokeilu2"
      }
    ]
  }
}
```

### Return surveys.
pollSurveyInfo

#### Fields
id: ID!
startDay: Date!
endDay: Date!
days: Int!
maxBackQuestion: Int!
description: String
questionsSet: [surveyQuestion!]!
partisipantsSet: [UserSurvey!]!

### Return user survey info.
pollUserSurvey

#### Arguments
surveyId: Int //Survey Id.

#### Fields
id: ID!
device: DeviceQuery
surveyInfo: Survey
startDate: Date!
endDate: Date
approved: Boolean!
backQuestionAnswers: JSONString
feelingQuestionAnswers: JSONString
tripsSet: [dayTrips!]!

### Returns empty base questions.
pollSurveyQuestions

#### Arguments
questionType: String //Question type(background, feeling, somethingelse).
surveyId: Int //Selected survey Id.

#### Fields
id: ID!
startDay: Date!
endDay: Date!
days: Int!
maxBackQuestion: Int!
description: String
questionsSet: [surveyQuestion!]!
partisipantsSet: [UserSurvey!]!

### Return selected base question.
pollSurveyQuestion.

#### Arguments
questionId: Int //Selected question Id.

#### Fields
id: ID!
questionData: JSONString
questionType: QuestionsQuestionType!
isUse: Boolean!
description: String
surveyInfo: Survey

### Return user trips form selected day.
pollDayTrips

#### Arguments
day: Date //Selected day.
surveyId: Int //Selected survey Id.

#### Fields
id: ID!
partisipant: UserSurvey
startTime: DateTime!
endTime: DateTime
originalTrip: Boolean
deleted: Boolean
approved: Boolean!
startMunicipality: String
endMunicipality: String
legsSet: [tripsLegs!]!
userPurpose: String

### Return trip legs.
pollTripsLegs

#### Arguments
tripId: Int // Selected trip Id.

#### Fields
id: ID!
trip: dayTrips
startTime: DateTime!
endTime: DateTime!
tripLength: Float
carbonFootprint: Float
nrPassengers: Int
transportMode: String
startLoc: PointScalar
endLoc: PointScalar
originalLeg: Boolean
deleted: Boolean

### Device information.
deviceData

#### Fields
id: ID!
uuid: UUID!
token: String
platform: String
systemVersion: String
brand: String
model: String
surveyEnabled: Boolean
mocafEnabled: Boolean
friendlyName: String
debugLogLevel: Int
debuggingEnabledAt: DateTime
customConfig: JSONString
accountKey: String
healthImpactEnabled: Boolean!
enabledAt: DateTime
disabledAt: DateTime
createdAt: DateTime
lastProcessedDataReceivedAt: DateTime
trips: [Trip!]!
partisipantsSet: [UserSurvey!]!

