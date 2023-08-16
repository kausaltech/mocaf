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

#### Parameters
//days: User survey days
//startDay: Survey start day
//endDay: Survey end day
///description: Survey description
///maxBackQuestion: Amount of different survey questions, default 3


### Add user to survey. Select randomly survey days to user.

pollEnrollToSurvey

#### Parameters
//surveyId: Id of survey, where to take part.
///backQuestionAnswers: User answers to back question on JSON form
///feelingQuestionAnswers: User answer to feeling questions on JSON form

### Add trip to user. User trip times needs to be unigue. Returns trip Id.

pollAddTrip

#### Parameters
//startTime: Trip start time
//endTime: Trip end time
//surveyId: Survey Id
///purpose: Trip purpose (tyo, opiskelu, tyoasia, vapaaaika, ostos, muu) Default empty
///startMunicipality: Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu) Default Tampere
///endMunicipality: Trip end municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu) Default Tampere

### Add leg of the trip. Leg times need to be unigue. Trip needs to be unapproved.

pollAddLeg

#### Parameters
//tripId: Trip Id
//startTime: Leg start time
//endTime: Leg end time
///tripLength: Lengt of the trip
///transportMode: Transport mode of the trip
///nrPassengers: Amount of passengers
///startLoc: Leg start location
///endLoc: Leg end location
///carbonFootprint: Leg carbon footprint

### Update given information to trip. Trip times needs to be unigue. Its not possible to approve unpurpose or empty trip.

pollEditTrip

#### Parameters
//tripId: Trip Id
//surveyId: Survey Id
///startTime: Trip start time
///endTime: Trip end time
///purpose: Trip purpose (tyo, opiskelu, tyoasia, vapaaaika, ostos, muu)
///startMunicipality: Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu)
///endMunicipality: Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu)
///approved: Approved (True/False)

### Mark user day ready. Chk that all day trip has purpose and leg.

pollMarkUserDayReady

#### Parameters
//selectedDate: Selected day
//surveyId: Survey Id

### Mark user survey ready. Chk that all day has been approved.

pollApproveUserSurvey

#### Parameters
//surveyId: Survey Id

### Register user to lottery.

pollEnrollLottery

#### Parameters
//name: Name
//email: Email

### Add empty question set in JSON form to database.

pollAddQuestion

#### Parameters
//description: Description
//question: Question in JSON form
//questionType: Question type (background, feeling, somethingelse)
///surveyId: Survey Id, where Question belongs

### Add locations to leg. Chk time of the leg.

pollLocationToLeg

#### Parameters
//loc: Loc point
//legId: Leg Id
//time: Point time

### Delete trip. Only unapproved trip can be deleted.

pollDelTrip

#### Parameters
//tripId: Trip Id
//surveyId: Survey Id

### Delete leg from the trip. Only leg from unapproved trip can be deleted.

pollDelLeg

#### Parameters
//tripId: Trip Id
//legId: Leg Id
//surveyId: Survey Id

### Compine two trip to one. Only unapproved trip can be compine.

pollJoinTrip

#### Parameters
//tripId: First trip Id
//trip2Id: Second trip Id
//surveyId: Survey Id

### Split one trip to two. Only unapproved trip can be split.

pollSplitTrip

#### Parameters
//tripId: Trip Id
//afterLegId: Last leg of first trip.
//surveyId: Survey Id

### Saves user answers to question.

pollAddUserAnswerToQuestions

#### Parameters
//surveyId: Survey Id
///backQuestionAnswers: User answers to back question on JSON form
///feelingQuestionAnswers: User answer to feeling questions on JSON form

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

### Return user survey info.

pollUserSurvey

#### Parameters
///surveyId: Survey Id

### Returns empty base questions.

pollSurveyQuestions

#### Parameters
//questionType: Question type(background, feeling, somethingelse)
///surveyId: Survey Id

### Return selected base question.

pollSurveyQuestion.

#### Parameters
//questionId

### Return user trips form selected day.

pollDayTrips

#### Parameters
//day: Selected day
///surveyId: Survey Id

### Return trip legs.

pollTripsLegs

#### Parameters
//tripId: Trip Id

### Device information.

deviceData

#### Parameters
///id
///uuid
///token
///platform
///systemVersion
///brand
///model
///surveyEnabled
///mocafEnabled
///friendlyName
///debugLogLevel
///debuggingEnabledAt
///customConfig
///accountKey
///healthImpactEnabled
///enabledAt
///disabledAt
///createdAt
///lastProcessedDataReceivedAt
///trips
///partisipantsSet

